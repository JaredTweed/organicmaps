#include "traffic/historical_traffic.hpp"
#include "historical_traffic_fixture.hpp"
#include "testing/testing.hpp"

#include <algorithm>
#include <stdexcept>
#include <vector>

namespace
{
using traffic::HistoricalTraffic;
std::vector<uint8_t> Fixture()
{
  return {std::begin(kHistoricalTrafficFixture), std::end(kHistoricalTrafficFixture)};
}
HistoricalTraffic Load()
{
  return HistoricalTraffic::Deserialize(Fixture(), "Synthetic", 1767225600, 12345, "AAAAAAAAAAAA");
}
bool Reject(std::vector<uint8_t> bytes, std::string const & region = "Synthetic", uint64_t build = 1767225600,
            uint64_t size = 12345, std::string const & hash = "AAAAAAAAAAAA")
{
  try
  {
    (void)HistoricalTraffic::Deserialize(std::move(bytes), region, build, size, hash);
  }
  catch (std::runtime_error const &)
  {
    return true;
  }
  return false;
}

UNIT_TEST(HistoricalTraffic_DirectionsAndInterpolation)
{
  auto const traffic = Load();
  TEST_EQUAL(traffic.GetSegmentCount(), 3, ());
  TEST_EQUAL(traffic.GetValidFrom(), 1767225600, ());
  TEST_EQUAL(traffic.GetValidUntil(), 1798761600, ());
  auto const east = HistoricalTraffic::SegmentKey(7, 0, true);
  auto const west = HistoricalTraffic::SegmentKey(7, 0, false);
  // Monday 2026-01-05, Chicago UTC-6: 06:00, 06:30, 07:00.
  TEST_EQUAL(*traffic.GetSpeedKMpH(east, 1767614400), 60.0, ());
  TEST_EQUAL(*traffic.GetSpeedKMpH(east, 1767616200), 40.0, ());
  TEST_EQUAL(*traffic.GetSpeedKMpH(east, 1767618000), 20.0, ());
  TEST_EQUAL(*traffic.GetSpeedKMpH(west, 1767618000), 40.0, ());
  TEST(!traffic.GetSpeedKMpH(HistoricalTraffic::SegmentKey(7, 1, true), 1767618000), ());
}

UNIT_TEST(HistoricalTraffic_CalendarAndBoundaries)
{
  auto const traffic = Load();
  auto const east = HistoricalTraffic::SegmentKey(7, 0, true);
  // Saturday morning; weekday congestion must not leak into weekends.
  TEST_EQUAL(*traffic.GetSpeedKMpH(east, 1768050000), 60.0, ());
  // July 1: supported synthetic holiday adjustment, local 07:00 (UTC-5).
  TEST_EQUAL(*traffic.GetSpeedKMpH(east, 1782907200), 15.0, ());
  // Spring DST transition: Sunday 01:59 -> 03:00; no missing wall hour to resolve.
  TEST_EQUAL(*traffic.GetSpeedKMpH(east, 1772956800), 50.0, ());
  TEST_EQUAL(*traffic.GetSpeedKMpH(east, 1772953200), 10.0, ());
  // Fall repeated 01:30: both UTC instants use the same local weekly bucket.
  TEST_EQUAL(*traffic.GetSpeedKMpH(east, 1793514600), 20.0, ());
  TEST_EQUAL(*traffic.GetSpeedKMpH(east, 1793518200), 20.0, ());
  // Sunday 23:30 -> Monday 00:00 interpolates across the weekly wrap.
  TEST_EQUAL(*traffic.GetSpeedKMpH(east, 1767591000), 70.0, ());
  // UTC and Chicago segments consult their own calendars.
  TEST_EQUAL(*traffic.GetSpeedKMpH(HistoricalTraffic::SegmentKey(8, 1, true), 1767618000), 90.0, ());
  TEST(!traffic.GetSpeedKMpH(east, 1767225599), ());
  TEST(!traffic.GetSpeedKMpH(east, 1798761600), ());
  TEST(!traffic.GetSpeedKMpH(east, -1), ());
  TEST_GREATER(traffic.GetMemorySize(), sizeof(kHistoricalTrafficFixture), ());
}

// Repair CRC after structural mutations so validation is tested independently of integrity checks.
void RepairChecksum(std::vector<uint8_t> & bytes)
{
  uint32_t crc = 0xffffffff;
  for (size_t i = 0; i < bytes.size() - 4; ++i)
  {
    crc ^= bytes[i];
    for (int bit = 0; bit < 8; ++bit)
      crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  }
  crc ^= 0xffffffff;
  for (size_t i = 0; i < 4; ++i)
    bytes[bytes.size() - 4 + i] = (crc >> (8 * i)) & 255;
}

UNIT_TEST(HistoricalTraffic_StructuralValidationAndMissingBuckets)
{
  auto bytes = Fixture();
  size_t pos = 40;
  for (int s = 0; s < 3; ++s)
    pos += 2 + bytes[pos] + 256 * bytes[pos + 1];
  size_t const profiles = pos + 8;
  for (auto const [offset, value] :
       std::vector<std::pair<size_t, uint8_t>>{{4, 2}, {6, 1}, {pos, 0}, {profiles, 201}, {bytes.size() - 8, 255}})
  {
    bytes = Fixture();
    bytes[offset] = value;
    RepairChecksum(bytes);
    TEST(Reject(bytes), (offset));
  }
  bytes = Fixture();
  bytes[bytes.size() - 5] = 64;  // Last record: UTC segment scale = 0.5.
  RepairChecksum(bytes);
  auto scaled = HistoricalTraffic::Deserialize(bytes, "Synthetic", 1767225600, 12345, "AAAAAAAAAAAA");
  TEST_EQUAL(*scaled.GetSpeedKMpH(HistoricalTraffic::SegmentKey(8, 1, true), 1767618000), 45.0, ());
  bytes[bytes.size() - 5] = 255;
  std::fill(bytes.begin() + profiles + 336, bytes.begin() + profiles + 504, 200);
  RepairChecksum(bytes);
  scaled = HistoricalTraffic::Deserialize(bytes, "Synthetic", 1767225600, 12345, "AAAAAAAAAAAA");
  TEST_EQUAL(*scaled.GetSpeedKMpH(HistoricalTraffic::SegmentKey(8, 1, true), 1767618000), 200.0, ());

  bytes = Fixture();
  bytes[profiles] = 0;  // Monday 00:00 is unobserved: preserve the road estimator.
  RepairChecksum(bytes);
  auto const traffic = HistoricalTraffic::Deserialize(std::move(bytes), "Synthetic", 1767225600, 12345, "AAAAAAAAAAAA");
  TEST(!traffic.GetSpeedKMpH(HistoricalTraffic::SegmentKey(7, 0, true), 1767592800), ());
}

UNIT_TEST(HistoricalTraffic_RepairedChecksumMutations)
{
  uint32_t random = 10062;
  for (unsigned i = 0; i < 512; ++i)
  {
    auto bytes = Fixture();
    random = random * 1664525 + 1013904223;
    bytes[random % (bytes.size() - 4)] ^= 1 << (i % 8);
    RepairChecksum(bytes);
    try
    {
      auto const traffic =
          HistoricalTraffic::Deserialize(std::move(bytes), "Synthetic", 1767225600, 12345, "AAAAAAAAAAAA");
      // Mutations to metadata or valid speed values can be accepted; every accepted table must be safe to query.
      (void)traffic.GetSpeedKMpH(HistoricalTraffic::SegmentKey(7, 0, true), 1767618000);
      (void)traffic.GetSpeedKMpH(HistoricalTraffic::SegmentKey(8, 1, false), 1793516400);
    }
    catch (std::runtime_error const &)
    {}
  }
}

UNIT_TEST(HistoricalTraffic_RejectMalformedAndIncompatible)
{
  TEST(Reject(Fixture(), "Other"), ());
  TEST(Reject(Fixture(), "Synthetic", 1767225600, 12345, "BBBBBBBBBBBB"), ());
  TEST(Reject(Fixture(), "Synthetic", 1767225601), ());
  TEST(Reject(Fixture(), "Synthetic", 1767225600, 12346), ());
  auto const original = Fixture();
  for (size_t n = 0; n < original.size(); ++n)
    TEST(Reject({original.begin(), original.begin() + n}), (n));
  for (size_t n = 0; n < original.size(); ++n)
  {
    auto bytes = original;
    bytes[n] ^= 1;
    TEST(Reject(std::move(bytes)), (n));
  }
}
}  // namespace
