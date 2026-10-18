#include "testing/testing.hpp"

#include "generator/generator_tests_support/test_feature.hpp"
#include "generator/generator_tests_support/test_generator.hpp"
#include "generator/generator_tests_support/test_mwm_builder.hpp"
#include "generator/traffic_generator.hpp"

#include "routing/checkpoints.hpp"
#include "routing/data_source.hpp"
#include "routing/edge_estimator.hpp"
#include "routing/geometry.hpp"
#include "routing/index_router.hpp"
#include "routing/route.hpp"
#include "routing/router_delegate.hpp"
#include "routing/routing_callbacks.hpp"
#include "routing/traffic_stash.hpp"

#include "routing_common/maxspeed_conversion.hpp"

#include "traffic/traffic_tests/historical_traffic_fixture.hpp"

#include "indexer/classificator_loader.hpp"

#include "platform/measurement_utils.hpp"
#include "platform/platform_tests_support/scoped_dir.hpp"
#include "platform/settings.hpp"

#include "geometry/mercator.hpp"
#include "geometry/tree4d.hpp"

#include "base/file_name_utils.hpp"
#include "base/scope_guard.hpp"

#include "coding/blake3.hpp"
#include "coding/file_reader.hpp"
#include "coding/file_writer.hpp"
#include "coding/files_container.hpp"

#include "platform/platform.hpp"

#include <zlib.h>

#include <algorithm>
#include <fstream>
#include <iterator>
#include <set>
#include <string>
#include <vector>

namespace routing_historical_traffic_test
{
using namespace routing;
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
}  // namespace routing_historical_traffic_test

namespace routing_historical_traffic_test
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
    TEST(!traffic::ExportHistoricalTrafficSegments(path, path), ());
    TEST_EQUAL(coding::Blake3::CalculateMwmBase64(path), hash, ("Reject overwriting the input map"));
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

void PutLE(std::vector<uint8_t> & bytes, uint64_t value, size_t n)
{
  for (size_t i = 0; i < n; ++i)
    bytes.push_back(static_cast<uint8_t>(value >> (8 * i)));
}

void PutVarUint(std::vector<uint8_t> & bytes, uint64_t value)
{
  while (value >= 128)
  {
    bytes.push_back(static_cast<uint8_t>((value & 127) | 128));
    value >>= 7;
  }
  bytes.push_back(static_cast<uint8_t>(value));
}

void PutString(std::vector<uint8_t> & bytes, std::string const & value)
{
  PutLE(bytes, value.size(), 2);
  bytes.insert(bytes.end(), value.begin(), value.end());
}

std::vector<uint8_t> MakeTrafficPackage(std::string const & region, uint64_t mapBuild, uint64_t mapSize,
                                        std::string const & mapHash, std::set<uint64_t> const & keys, uint8_t speedKMpH,
                                        bool increasingMondaySpeed = false)
{
  constexpr int64_t kValidFrom = 1767225600;   // 2026-01-01
  constexpr int64_t kValidUntil = 1798761600;  // 2027-01-01
  std::vector<uint8_t> bytes{'O', 'M', 'H', 'T'};
  PutLE(bytes, 1, 2);  // Version.
  PutLE(bytes, 0, 2);  // Flags.
  PutLE(bytes, mapBuild, 8);
  PutLE(bytes, mapSize, 8);
  PutLE(bytes, kValidFrom, 8);
  PutLE(bytes, kValidUntil, 8);
  PutString(bytes, region);
  PutString(bytes, mapHash);
  PutString(bytes, "{\"name\":\"end-to-end synthetic test\",\"license\":\"CC0-1.0\",\"synthetic\":true}");
  PutLE(bytes, 1, 2);  // Profiles.
  PutLE(bytes, 1, 2);  // Timezones.
  PutLE(bytes, keys.size(), 4);
  bytes.insert(bytes.end(), 168, speedKMpH);
  if (increasingMondaySpeed)
    bytes[bytes.size() - 168 + 14] = 2;  // Monday 14:00, one hour after departure.

  PutLE(bytes, 1, 2);  // Transitions.
  PutLE(bytes, 0, 2);  // Date adjustments.
  PutLE(bytes, kValidFrom, 8);
  PutLE(bytes, 0, 4);  // UTC.
  uint64_t previous = 0;
  size_t i = 0;
  for (uint64_t key : keys)
  {
    PutVarUint(bytes, i % 64 == 0 ? key : key - previous);
    PutLE(bytes, 0, 2);    // Profile.
    PutLE(bytes, 0, 1);    // Timezone.
    PutLE(bytes, 128, 1);  // Factor = 1.
    previous = key;
    ++i;
  }
  PutLE(bytes, crc32(0, bytes.data(), bytes.size()), 4);
  return bytes;
}

UNIT_TEST(HistoricalTraffic_MapIdentityFollowsRegistration)
{
  classificator::Load();
  platform::tests_support::ScopedDir dir("historical_traffic_identity");
  platform::LocalCountryFile file(dir.GetFullPath(), platform::CountryFile("Synthetic"), 0);
  {
    generator::tests_support::TestMwmBuilder builder(file, feature::DataHeader::MapType::Country);
    builder.Add(generator::tests_support::TestRoad({{0.0, 0.0}, {0.01, 0.01}}, "Road", "en"));
  }
  auto const path = file.GetPath(MapFileType::Map);
  auto const ids = std::make_shared<NumMwmIds>();
  ids->RegisterFile(file.GetCountryFile());
  traffic::TrafficCache cache;
  auto const stash = std::make_shared<TrafficStash>(cache, ids);
  std::string previousHash;
  uint64_t previousSize = 0;
  for (char value : {'a', 'b'})
  {
    {
      FilesContainerW writer(path, FileWriter::OP_WRITE_EXISTING);
      writer.Write(&value, 1, "historical_identity_test");
    }
    TEST(Platform::SetFileModificationTime(path, 1700000000), ());
    auto const hash = coding::Blake3::CalculateMwmBase64(path);
    auto const size = FileReader(path).Size();
    if (!previousHash.empty())
    {
      TEST_NOT_EQUAL(hash, previousHash, ());
      TEST_EQUAL(size, previousSize, ("Replacement deliberately has identical size and mtime"));
    }
    platform::LocalCountryFile registered(dir.GetFullPath(), platform::CountryFile("Synthetic"), 0);
    registered.SyncWithDisk();
    FrozenDataSource dataSource;
    TEST_EQUAL(dataSource.RegisterMap(registered).second, MwmSet::RegResult::Success, ());
    MwmDataSource source(dataSource, ids);
    auto const build = source.GetMwmValue(0).GetMwmVersion().GetSecondsSinceEpoch();
    auto install = [&](std::string const & expectedHash)
    {
      auto const bytes = MakeTrafficPackage("Synthetic", build, size, expectedHash, {0}, 20);
      FileWriter writer(path + ".traffic");
      writer.Write(bytes.data(), bytes.size());
    };
    Segment const segment(0, 0, 0, true);
    if (!previousHash.empty())
    {
      install(previousHash);
      TrafficStash::Guard guard(stash);
      TEST(!stash->GetHistoricalSpeed(segment, 1767618000, source),
           ("A new registration must not reuse the previous map digest"));
    }
    install(hash);
    {
      TrafficStash::Guard guard(stash);
      auto const speed = stash->GetHistoricalSpeed(segment, 1767618000, source);
      TEST(speed.has_value(), ());
      TEST_EQUAL(*speed, 20.0, ());
    }
    previousHash = hash;
    previousSize = size;
  }
  FileWriter::DeleteFileX(path + ".traffic");
  FileWriter::DeleteFileX(path);
}

class TestTrafficCache : public traffic::TrafficCache
{
public:
  using traffic::TrafficCache::Set;
};

void CheckHistoricalRouteEta(platform::LocalCountryFile const & file, ms::LatLon const & startLatLon,
                             ms::LatLon const & finishLatLon)
{
  bool previousEnabled = false;
  bool const hadSetting = settings::Get(kOfflineHistoricalTrafficEnabled, previousEnabled);
  SCOPE_GUARD(restoreSetting, [&]
  {
    if (hadSetting)
      settings::Set(kOfflineHistoricalTrafficEnabled, previousEnabled);
    else
      settings::Delete(kOfflineHistoricalTrafficEnabled);
  });
  settings::Set(kOfflineHistoricalTrafficEnabled, false);
  auto const path = file.GetPath(MapFileType::Map);
  auto const region = file.GetCountryName();
  FrozenDataSource dataSource;
  platform::LocalCountryFile downloaded(
      file.GetDirectory(),
      platform::CountryFile(region, FileReader(path).Size(), coding::Blake3::CalculateMwmBase64(path)),
      file.GetVersion());
  downloaded.SyncWithDisk();
  auto const map = dataSource.RegisterMap(downloaded);
  TEST_EQUAL(map.second, MwmSet::RegResult::Success, ());
  auto const ids = std::make_shared<NumMwmIds>();
  ids->RegisterFile(platform::CountryFile(region));
  auto const tree = std::make_shared<m4::Tree<NumMwmId>>();
  auto const rect = map.first.GetInfo()->m_bordersRect;
  tree->Add(0, rect);
  auto const parent = [](std::string const &) { return std::string(); };
  auto const countryFile = [region](m2::PointD const &) { return region; };
  auto const countryRect = [rect](std::string const &) { return rect; };
  TestTrafficCache cache;
  IndexRouter router(VehicleType::Car, false, parent, countryFile, countryRect, ids, tree, cache, dataSource);
  int64_t const departure = 1767618000;
  router.SetCurrentTimeGetter([&] { return departure; });

  auto const start = mercator::FromLatLon(startLatLon);
  auto const finish = mercator::FromLatLon(finishLatLon);
  struct Snapshot
  {
    double m_time;
    size_t m_segments;
    std::set<uint64_t> m_keys;
    std::vector<Segment> m_path;
  };
  auto const calculate = [&]
  {
    RouterDelegate delegate;
    RoutesResult result("historical-test", 0);
    auto const code = router.CalculateRoute(Checkpoints(start, finish), {0.0, 0.0}, false /* adjust */,
                                            false /* needAlternatives */, delegate, result);
    TEST_EQUAL(code, RouterResultCode::NoError, ());
    TEST(result.IsValid(), ());
    auto const & active = result.GetActive();
    std::set<uint64_t> keys;
    std::vector<Segment> orderedPath;
    for (auto const & routeSegment : active.GetRouteSegments())
    {
      auto const & segment = routeSegment.GetSegment();
      orderedPath.push_back(segment);
      if (segment.IsRealSegment())
        keys.insert(traffic::HistoricalTraffic::SegmentKey(segment.GetFeatureId(), segment.GetSegmentIdx(),
                                                           segment.IsForward()));
    }
    return Snapshot{active.GetTotalTimeSec(), active.GetRouteSegments().size(), std::move(keys),
                    std::move(orderedPath)};
  };

  auto const baseline = calculate();
  TEST(!baseline.m_keys.empty(), ());
  auto coloring = std::make_shared<traffic::TrafficInfo::Coloring>();
  for (auto const & segment : baseline.m_path)
    if (segment.IsRealSegment() && segment.GetSegmentIdx() <= 65535)
      (*coloring)[traffic::TrafficInfo::RoadSegmentId(segment.GetFeatureId(), segment.GetSegmentIdx(),
                                                      segment.IsForward() ? 0 : 1)] = traffic::SpeedGroup::TempBlock;
  cache.Set(map.first, coloring);
  auto const withLegacyCache = calculate();
  TEST_ALMOST_EQUAL_ABS(withLegacyCache.m_time, baseline.m_time, 1e-3,
                        ("Historical traffic must not re-enable legacy live routing costs"));
  TEST(withLegacyCache.m_path == baseline.m_path, ());
  auto const handle = dataSource.GetMwmHandleById(map.first);
  TEST(handle.IsAlive(), ());
  auto const & value = *handle.GetValue();
  auto const package =
      MakeTrafficPackage(value.GetCountryFileName(), value.GetMwmVersion().GetSecondsSinceEpoch(),
                         FileReader(path).Size(), coding::Blake3::CalculateMwmBase64(path), baseline.m_keys, 1);
  {
    FileWriter writer(path + ".traffic");
    writer.Write(package.data(), package.size());
  }

  settings::Set(kOfflineHistoricalTrafficEnabled, true);
  auto const congested = calculate();
  TEST_EQUAL(congested.m_keys, baseline.m_keys, ("Traffic must not change the selected route"));
  TEST_EQUAL(congested.m_segments, baseline.m_segments, ());
  TEST(congested.m_path == baseline.m_path, ());
  TEST_GREATER(congested.m_time, baseline.m_time * 2.0, ());

  auto const varyingPackage =
      MakeTrafficPackage(value.GetCountryFileName(), value.GetMwmVersion().GetSecondsSinceEpoch(),
                         FileReader(path).Size(), coding::Blake3::CalculateMwmBase64(path), baseline.m_keys, 1, true);
  {
    FileWriter writer(path + ".traffic");
    writer.Write(varyingPackage.data(), varyingPackage.size());
  }
  auto const varying = calculate();
  TEST(varying.m_path == baseline.m_path, ());
  TEST_LESS(varying.m_time, congested.m_time * 0.99, ("Later segments must sample the advancing arrival clock"));
  TEST_GREATER(varying.m_time, congested.m_time * 0.5, ());

  settings::Set(kOfflineHistoricalTrafficEnabled, false);
  auto const disabled = calculate();
  TEST_ALMOST_EQUAL_ABS(disabled.m_time, baseline.m_time, 1e-3, ());

  settings::Set(kOfflineHistoricalTrafficEnabled, true);
  FileWriter::DeleteFileX(path + ".traffic");
  auto const missing = calculate();
  TEST_ALMOST_EQUAL_ABS(missing.m_time, baseline.m_time, 1e-3, ());
  settings::Set(kOfflineHistoricalTrafficEnabled, false);
}

UNIT_TEST(HistoricalTraffic_EndToEndGeneratedMapRouteEta)
{
  generator::tests_support::TestRawGenerator generator;
  generator.BuildFB(base::JoinPath(GetPlatform().ResourcesDir(), "test_data", "osm", "nsk_magadanskaya.osm"),
                    "Synthetic");
  generator.BuildFeatures("Synthetic");
  generator.BuildRouting("Synthetic", "Synthetic");
  generator.BuildCrossMwm("Synthetic", "Synthetic");
  CheckHistoricalRouteEta(platform::LocalCountryFile::MakeTemporary(generator.GetMwmPath("Synthetic")),
                          {55.074347, 82.939134}, {55.076779, 82.935965});
}

}  // namespace routing_historical_traffic_test
