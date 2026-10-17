#include "generator/traffic_generator.hpp"

#include "routing/routing_helpers.hpp"

#include "traffic/traffic_info.hpp"

#include "routing_common/car_model.hpp"

#include "platform/mwm_traits.hpp"
#include "platform/mwm_version.hpp"

#include "indexer/feature_algo.hpp"
#include "indexer/feature_processor.hpp"
#include "indexer/features_offsets_table.hpp"

#include "geometry/mercator.hpp"

#include "coding/blake3.hpp"
#include "coding/file_reader.hpp"
#include "coding/file_writer.hpp"
#include "coding/files_container.hpp"

#include <fstream>
#include <iomanip>
#include <locale>
#include <vector>

namespace traffic
{
bool ExportHistoricalTrafficSegments(std::string const & mwmPath, std::string const & output)
{
  try
  {
    FilesContainerR container(mwmPath);
    auto const build = version::MwmVersion::Read(container).GetSecondsSinceEpoch();
    auto const size = FileReader(mwmPath).Size();
    auto const hash = coding::Blake3::CalculateMwmBase64(mwmPath);
    std::ofstream out(output);
    out.imbue(std::locale::classic());
    out.exceptions(std::ios::badbit | std::ios::failbit);
    out << "map_build,map_size,map_hash,feature_id,segment_idx,forward,start_lat,start_lon,end_lat,end_lon\n";
    out << std::setprecision(12);
    // Same road eligibility and BEST_GEOMETRY segmentation as ExtractTrafficKeys.
    feature::ForEachFeature(mwmPath, [&](FeatureType & ft, uint32_t const fid)
    {
      feature::TypesHolder const types(ft);
      auto const & model = routing::CarModel::AllLimitsInstance();
      if (!model.IsRoad(types))
        return;
      ft.ParseGeometry(FeatureType::BEST_GEOMETRY);
      for (uint32_t i = 0; i + 1 < ft.GetPointsCount(); ++i)
      {
        auto const a = mercator::ToLatLon(ft.GetPoint(i));
        auto const b = mercator::ToLatLon(ft.GetPoint(i + 1));
        out << build << ',' << size << ',' << hash << ',' << fid << ',' << i << ",true," << a.m_lat << ',' << a.m_lon
            << ',' << b.m_lat << ',' << b.m_lon << '\n';
        if (!model.IsOneWay(types))
          out << build << ',' << size << ',' << hash << ',' << fid << ',' << i << ",false," << b.m_lat << ',' << b.m_lon
              << ',' << a.m_lat << ',' << a.m_lon << '\n';
      }
    });
    out.close();
    return true;
  }
  catch (std::exception const & e)
  {
    LOG(LERROR, ("Cannot export historical traffic segments:", e.what()));
    return false;
  }
}

bool GenerateTrafficKeysFromDataFile(std::string const & mwmPath)
{
  try
  {
    std::vector<TrafficInfo::RoadSegmentId> keys;
    TrafficInfo::ExtractTrafficKeys(mwmPath, keys);

    std::vector<uint8_t> buf;
    TrafficInfo::SerializeTrafficKeys(keys, buf);

    FilesContainerW writeContainer(mwmPath, FileWriter::OP_WRITE_EXISTING);
    auto writer = writeContainer.GetWriter(TRAFFIC_KEYS_FILE_TAG);
    writer->Write(buf.data(), buf.size());
  }
  catch (RootException const & e)
  {
    LOG(LERROR, ("Failed to build traffic keys:", e.Msg()));
    return false;
  }

  return true;
}
}  // namespace traffic
