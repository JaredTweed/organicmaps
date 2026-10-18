#include "routing/traffic_stash.hpp"

#include "routing/data_source.hpp"

#include "platform/platform.hpp"

#include "coding/blake3.hpp"
#include "coding/file_reader.hpp"

#include "base/checked_cast.hpp"

#include <limits>
#include <stdexcept>
#include <string>

namespace routing
{
TrafficStash::TrafficStash(traffic::TrafficCache const & source, std::shared_ptr<NumMwmIds> numMwmIds,
                           bool useLiveTraffic)
  : m_useLiveTraffic(useLiveTraffic)
  , m_source(source)
  , m_numMwmIds(std::move(numMwmIds))
{
  CHECK(m_numMwmIds, ());
}

traffic::SpeedGroup TrafficStash::GetSpeedGroup(Segment const & segment) const
{
  if (!m_useLiveTraffic || segment.GetSegmentIdx() > std::numeric_limits<uint16_t>::max())
    return traffic::SpeedGroup::Unknown;
  auto itMwm = m_mwmToTraffic.find(segment.GetMwmId());
  if (itMwm == m_mwmToTraffic.cend())
    return traffic::SpeedGroup::Unknown;

  auto const & coloring = itMwm->second;
  auto const itSeg = coloring->find(traffic::TrafficInfo::RoadSegmentId(
      segment.GetFeatureId(), base::asserted_cast<uint16_t>(segment.GetSegmentIdx()),
      segment.IsForward() ? traffic::TrafficInfo::RoadSegmentId::kForwardDirection
                          : traffic::TrafficInfo::RoadSegmentId::kReverseDirection));

  if (itSeg == coloring->cend())
    return traffic::SpeedGroup::Unknown;

  return itSeg->second;
}

void TrafficStash::SetColoring(NumMwmId numMwmId, std::shared_ptr<traffic::TrafficInfo::Coloring const> coloring)
{
  m_mwmToTraffic[numMwmId] = coloring;
}

bool TrafficStash::Has(NumMwmId numMwmId) const
{
  return m_mwmToTraffic.find(numMwmId) != m_mwmToTraffic.cend();
}

std::optional<double> TrafficStash::GetHistoricalSpeed(Segment const & segment, int64_t utc, MwmDataSource & dataSource)
{
  auto const id = segment.GetMwmId();
  if (!m_numMwmIds->ContainsFileForMwm(id) || segment.GetSegmentIdx() >= (uint32_t{1} << 31))
    return {};
  auto [it, inserted] = m_historical.try_emplace(id);
  if (inserted)
  {
    try
    {
      auto const & handle = dataSource.GetHandle(id);
      if (handle.IsAlive())
      {
        auto const & value = *handle.GetValue();
        auto const path = value.m_file.GetPath(MapFileType::Map);
        uint64_t mapSize = 0;
        uint64_t packageSize = 0;
        if (Platform::GetFileSizeByFullPath(path, mapSize) &&
            Platform::GetFileSizeByFullPath(path + ".traffic", packageSize) &&
            packageSize <= traffic::HistoricalTraffic::kMaxPackageSize)
        {
          FileReader reader(path + ".traffic");
          std::vector<uint8_t> bytes(packageSize);
          reader.Read(0, bytes.data(), bytes.size());
          // Storage verifies downloaded maps; reuse that identity just as other map readers do.
          auto hash = value.m_file.GetCountryFile().GetHash();
          if (hash.empty())
          {
            auto identity = m_mapIdentities.find(id);
            if (identity == m_mapIdentities.end() || identity->second.m_info.lock() != handle.GetInfo())
            {
              auto digest = coding::Blake3::CalculateMwmBase64(path);
              if (m_mapIdentities.size() >= 64)
                m_mapIdentities.clear();
              identity = m_mapIdentities.insert_or_assign(id, MapIdentity{handle.GetInfo(), std::move(digest)}).first;
            }
            hash = identity->second.m_hash;
          }
          it->second =
              traffic::HistoricalTraffic::Deserialize(std::move(bytes), value.GetCountryFileName(),
                                                      value.GetMwmVersion().GetSecondsSinceEpoch(), mapSize, hash);
        }
      }
    }
    catch (Reader::Exception const & e)
    {
      LOG(LWARNING, ("Cannot read historical traffic package:", e.what()));
    }
    catch (std::runtime_error const & e)
    {
      LOG(LWARNING, ("Ignoring invalid historical traffic package for", m_numMwmIds->GetFile(id).GetName(), e.what()));
    }
  }
  if (!it->second)
    return {};
  return it->second->GetSpeedKMpH(
      traffic::HistoricalTraffic::SegmentKey(segment.GetFeatureId(), segment.GetSegmentIdx(), segment.IsForward()),
      utc);
}

void TrafficStash::CopyTraffic()
{
  if (!m_useLiveTraffic)
    return;
  traffic::AllMwmTrafficInfo copy;
  m_source.CopyTraffic(copy);
  for (auto const & kv : copy)
  {
    auto const numMwmId = m_numMwmIds->GetId(kv.first.GetInfo()->GetLocalFile().GetCountryFile());
    CHECK(kv.second, ());
    SetColoring(numMwmId, kv.second);
  }
}
}  // namespace routing
