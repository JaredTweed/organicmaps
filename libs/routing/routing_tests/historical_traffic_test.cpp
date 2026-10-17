#include "testing/testing.hpp"

#include "generator/generator_tests_support/test_feature.hpp"
#include "generator/generator_tests_support/test_mwm_builder.hpp"
#include "generator/traffic_generator.hpp"

#include "routing/data_source.hpp"
#include "routing/edge_estimator.hpp"
#include "routing/geometry.hpp"
#include "routing/traffic_stash.hpp"

#include "routing_common/maxspeed_conversion.hpp"

#include "traffic/traffic_tests/historical_traffic_fixture.hpp"

#include "indexer/classificator_loader.hpp"

#include "platform/measurement_utils.hpp"
#include "platform/platform_tests_support/scoped_dir.hpp"

#include "coding/blake3.hpp"
#include "coding/file_reader.hpp"
#include "coding/file_writer.hpp"

#include <zlib.h>

#include <algorithm>
#include <fstream>
#include <iterator>

using namespace routing;

namespace
{
UNIT_TEST(HistoricalTraffic_DrivingEtaOnlyAndFallback)
{
  RoadGeometry const road(false, Maxspeed(measurement_utils::Units::Metric, 60, 60),
                          RoadGeometry::Points({{0.0, 0.0}, {0.0, 0.01}}));
  Segment const segment(0, 7, 0, true);
  for (auto mode : {VehicleType::Car, VehicleType::Bicycle, VehicleType::Pedestrian, VehicleType::Transit})
  {
    auto estimator = EdgeEstimator::Create(mode, 200, {1.0, 1.0}, nullptr, nullptr, nullptr);
    auto calc = [&](EdgeEstimator::Purpose purpose) { return estimator->CalcSegmentWeight(segment, road, purpose); };
    auto const baseline = calc(EdgeEstimator::Purpose::ETA);
    auto const weight = calc(EdgeEstimator::Purpose::Weight);
    auto const turn = estimator->GetUTurnPenalty(EdgeEstimator::Purpose::ETA);
    unsigned calls = 0;
    estimator->SetHistoricalTraffic([&](Segment const & s, int64_t utc) -> std::optional<double>
    {
      ++calls;
      TEST_EQUAL(s.GetFeatureId(), 7, ());
      TEST_EQUAL(utc, 1767618000, ());
      return 20.0;
    });
    estimator->SetHistoricalTrafficTime(1767618000);
    auto const congested = calc(EdgeEstimator::Purpose::ETA);
    TEST_EQUAL(calc(EdgeEstimator::Purpose::Weight), weight, ());
    TEST_EQUAL(estimator->GetUTurnPenalty(EdgeEstimator::Purpose::ETA), turn, ());
    if (mode == VehicleType::Car)
    {
      TEST_ALMOST_EQUAL_ABS(congested, baseline * 3, 1e-6, ());
      TEST_EQUAL(calls, 1, ());
    }
    else
    {
      TEST_EQUAL(congested, baseline, ());
      TEST_EQUAL(calls, 0, ());
    }
    estimator->SetHistoricalTraffic([](Segment const &, int64_t) -> std::optional<double> { return {}; });
    TEST_EQUAL(calc(EdgeEstimator::Purpose::ETA), baseline, ());
    estimator->SetHistoricalTraffic([](Segment const &, int64_t) -> std::optional<double> { return 0.0; });
    TEST_EQUAL(calc(EdgeEstimator::Purpose::ETA), baseline, ());
    estimator->SetHistoricalTraffic({});
    TEST_EQUAL(calc(EdgeEstimator::Purpose::ETA), baseline, ());
  }
}

UNIT_TEST(HistoricalTraffic_PreservesLiveTrafficAndClosures)
{
  traffic::TrafficCache cache;
  auto const ids = std::make_shared<NumMwmIds>();
  auto const stash = std::make_shared<TrafficStash>(cache, ids);
  auto const coloring = std::make_shared<traffic::TrafficInfo::Coloring>();
  auto const estimator = EdgeEstimator::Create(VehicleType::Car, 200, {1.0, 1.0}, stash, nullptr, ids);
  RoadGeometry const road(false, Maxspeed(measurement_utils::Units::Metric, 60, 60),
                          RoadGeometry::Points({{0.0, 0.0}, {0.0, 0.01}}));
  Segment const segment(0, 7, 0, true);
  stash->SetColoring(0, coloring);
  for (auto group : {traffic::SpeedGroup::TempBlock, traffic::SpeedGroup::G3, traffic::SpeedGroup::G5})
  {
    (*coloring)[traffic::TrafficInfo::RoadSegmentId(7, 0, 0)] = group;
    estimator->SetHistoricalTraffic({});
    auto const live = estimator->CalcSegmentWeight(segment, road, EdgeEstimator::Purpose::ETA);
    estimator->SetHistoricalTraffic([](Segment const &, int64_t) -> std::optional<double>
    {
      TEST(false, ("Available live traffic must take precedence"));
      return 20.0;
    });
    TEST_EQUAL(estimator->CalcSegmentWeight(segment, road, EdgeEstimator::Purpose::ETA), live, ());
  }
}
}  // namespace

namespace
{
UNIT_TEST(HistoricalTraffic_ManualPackageLifecycleAndSegmentExport)
{
  classificator::Load();
  platform::tests_support::ScopedDir dir("historical_traffic_lifecycle");
  platform::LocalCountryFile file(dir.GetFullPath(), platform::CountryFile("Synthetic"), 0);
  {
    generator::tests_support::TestMwmBuilder builder(file, feature::DataHeader::MapType::Country);
    for (int i = 0; i < 9; ++i)
      builder.Add(generator::tests_support::TestRoad({{0.0, i * 0.02}, {0.01, i * 0.02 + 0.01}, {0.02, i * 0.02}},
                                                     "Synthetic road " + std::to_string(i), "en"));
  }
  auto const path = file.GetPath(MapFileType::Map);
  auto const csv = dir.GetFullPath() + "/segments.csv";
  auto const hash = coding::Blake3::CalculateMwmBase64(path);
  {
    FrozenDataSource dataSource;
    TEST_EQUAL(dataSource.RegisterMap(file).second, MwmSet::RegResult::Success, ());
    auto const ids = std::make_shared<NumMwmIds>();
    ids->RegisterFile(file.GetCountryFile());
    MwmDataSource source(dataSource, ids);
    traffic::TrafficCache cache;
    auto const stash = std::make_shared<TrafficStash>(cache, ids);
    auto const & map = source.GetMwmValue(0);
    std::vector<uint8_t> bytes(std::begin(kHistoricalTrafficFixture), std::end(kHistoricalTrafficFixture));
    auto put = [&](size_t pos, uint64_t value, size_t n)
    {
      for (size_t i = 0; i < n; ++i)
        bytes[pos + i] = (value >> (8 * i)) & 255;
    };
    put(8, map.GetMwmVersion().GetSecondsSinceEpoch(), 8);
    put(16, FileReader(path).Size(), 8);
    // Synthetic's nine-byte region name is followed by a length-prefixed twelve-byte map hash.
    std::copy(hash.begin(), hash.end(), bytes.begin() + 53);
    auto install = [&]
    {
      put(bytes.size() - 4, crc32(0, bytes.data(), bytes.size() - 4), 4);
      FileWriter writer(path + ".traffic");
      writer.Write(bytes.data(), bytes.size());
    };
    Segment const segment(0, 7, 0, true);
    {
      TrafficStash::Guard guard(stash);
      TEST(!stash->GetHistoricalSpeed(segment, 1767618000, source), ());
      install();
      TEST(!stash->GetHistoricalSpeed(segment, 1767618000, source), ("Absent package is cached for this calculation"));
    }
    {
      TrafficStash::Guard guard(stash);
      TEST_EQUAL(*stash->GetHistoricalSpeed(segment, 1767618000, source), 20.0, ());
      FileWriter::DeleteFileX(path + ".traffic");
      TEST_EQUAL(*stash->GetHistoricalSpeed(segment, 1767618000, source), 20.0, ("Active snapshot survives removal"));
    }
    {
      TrafficStash::Guard guard(stash);
      TEST(!stash->GetHistoricalSpeed(segment, 1767618000, source), ("Removal takes effect next calculation"));
    }
    bytes[53] ^= 1;
    install();
    {
      TrafficStash::Guard guard(stash);
      TEST(!stash->GetHistoricalSpeed(segment, 1767618000, source), ("Wrong map hash must fall back"));
    }
    TEST(traffic::ExportHistoricalTrafficSegments(path, csv), ());
    std::ifstream stream(csv);
    std::string const exported{std::istreambuf_iterator<char>(stream), {}};
    TEST(exported.find(hash) != std::string::npos, ());
    TEST(exported.find(",true,") != std::string::npos, ());
    TEST(exported.find(",false,") != std::string::npos, ());
    TEST_EQUAL(coding::Blake3::CalculateMwmBase64(path), hash, ("Export must not modify the map"));
  }
  FileWriter::DeleteFileX(csv);
  FileWriter::DeleteFileX(path + ".traffic");
  FileWriter::DeleteFileX(path);
}
}  // namespace
