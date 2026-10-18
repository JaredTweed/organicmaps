#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace traffic
{
// Immutable after loading. No observations, device locations or network access are needed at runtime.
class HistoricalTraffic
{
public:
  static constexpr uint32_t kBlockSize = 64;
  static constexpr uint64_t kMaxPackageSize = 128 * 1024 * 1024;

  // Throws std::runtime_error for malformed, unsupported or incompatible packages.
  static HistoricalTraffic Deserialize(std::vector<uint8_t> bytes, std::string const & region, uint64_t mapBuild,
                                       uint64_t mapSize, std::string const & mapHash);
  static uint64_t SegmentKey(uint32_t feature, uint32_t segment, bool forward);

  // UTC seconds at segment entry. Missing buckets, expired calendars and unknown segments return nullopt.
  std::optional<double> GetSpeedKMpH(uint64_t key, int64_t utc) const;
  size_t GetMemorySize() const;
  std::string const & GetSource() const { return m_source; }
  int64_t GetValidFrom() const { return m_validFrom; }
  int64_t GetValidUntil() const { return m_validUntil; }
  uint32_t GetSegmentCount() const { return m_segments; }

private:
  struct Transition
  {
    int64_t m_utc;
    int32_t m_offset;
  };
  struct Adjustment
  {
    int32_t m_localDay;
    uint8_t m_factor;
  };
  struct Zone
  {
    std::vector<Transition> m_transitions;
    std::vector<Adjustment> m_adjustments;
  };
  struct Block
  {
    uint64_t m_key;
    size_t m_offset;
  };
  std::vector<uint8_t> m_bytes;
  std::vector<Block> m_blocks;
  std::vector<Zone> m_zones;
  size_t m_profilesOffset = 0;
  std::string m_source;
  int64_t m_validFrom = 0;
  int64_t m_validUntil = 0;
  uint32_t m_segments = 0;
};
}  // namespace traffic
