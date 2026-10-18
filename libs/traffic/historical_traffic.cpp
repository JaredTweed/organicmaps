#include "traffic/historical_traffic.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <stdexcept>
#include <utility>

namespace traffic
{
namespace
{
void Require(bool condition)
{
  if (!condition)
    throw std::runtime_error("Invalid historical traffic package");
}

class Cursor
{
public:
  Cursor(std::vector<uint8_t> const & bytes, size_t pos = 0) : m_bytes(bytes), m_pos(pos) {}
  uint64_t Read(size_t n)
  {
    Require(n <= 8 && m_pos <= m_bytes.size() && n <= m_bytes.size() - m_pos);
    uint64_t value = 0;
    for (size_t i = 0; i < n; ++i)
      value |= uint64_t(m_bytes[m_pos++]) << (8 * i);
    return value;
  }
  uint64_t VarUint()
  {
    uint64_t value = 0;
    for (unsigned shift = 0; shift < 64; shift += 7)
    {
      auto const b = Read(1);
      Require(shift != 63 || b <= 1);
      value |= (b & 127) << shift;
      if (!(b & 128))
        return value;
    }
    throw std::runtime_error("Invalid traffic segment delta");
  }
  std::string String()
  {
    auto const n = Read(2);
    Require(n <= m_bytes.size() - m_pos);
    std::string s(m_bytes.begin() + m_pos, m_bytes.begin() + m_pos + n);
    m_pos += n;
    return s;
  }
  size_t Pos() const { return m_pos; }

private:
  std::vector<uint8_t> const & m_bytes;
  size_t m_pos;
};

uint32_t Crc32(std::vector<uint8_t> const & bytes)
{
  static auto const table = []
  {
    std::array<uint32_t, 256> result{};
    for (uint32_t i = 0; i < result.size(); ++i)
    {
      uint32_t c = i;
      for (unsigned j = 0; j < 8; ++j)
        c = (c >> 1) ^ ((c & 1) ? 0xedb88320 : 0);
      result[i] = c;
    }
    return result;
  }();
  uint32_t crc = 0xffffffff;
  for (size_t i = 0; i < bytes.size() - 4; ++i)
    crc = table[(crc ^ bytes[i]) & 255] ^ (crc >> 8);
  return crc ^ 0xffffffff;
}
}  // namespace

uint64_t HistoricalTraffic::SegmentKey(uint32_t feature, uint32_t segment, bool forward)
{
  // Organic Maps segments have a uint32 index. The top bit is reserved in this format.
  Require(segment < (uint32_t{1} << 31));
  return (uint64_t(feature) << 32) | (uint64_t(segment) << 1) | (forward ? 0 : 1);
}

HistoricalTraffic HistoricalTraffic::Deserialize(std::vector<uint8_t> bytes, std::string const & region,
                                                 uint64_t mapBuild, uint64_t mapSize, std::string const & mapHash)
{
  Require(bytes.size() >= 64 && bytes.size() <= kMaxPackageSize);
  Cursor checksum(bytes, bytes.size() - 4);
  Require(checksum.Read(4) == Crc32(bytes));
  Cursor r(bytes);
  Require(r.Read(4) == 0x54484d4f && r.Read(2) == 1 && r.Read(2) == 0);
  Require(r.Read(8) == mapBuild && r.Read(8) == mapSize);
  HistoricalTraffic result;
  result.m_validFrom = static_cast<int64_t>(r.Read(8));
  result.m_validUntil = static_cast<int64_t>(r.Read(8));
  Require(result.m_validFrom >= 946684800 && result.m_validUntil > result.m_validFrom &&
          result.m_validUntil <= 4102444800LL);
  Require(r.String() == region);
  Require(mapHash.size() == 12 && r.String() == mapHash);
  result.m_source = r.String();
  Require(!result.m_source.empty());
  auto const profiles = r.Read(2);
  auto const zones = r.Read(2);
  result.m_segments = static_cast<uint32_t>(r.Read(4));
  Require(profiles > 0 && zones > 0 && zones <= 256 && result.m_segments <= bytes.size() / 5);
  result.m_profilesOffset = r.Pos();
  for (size_t i = 0; i < profiles * 168; ++i)
    Require(r.Read(1) <= 200);
  result.m_zones.resize(zones);
  for (auto & zone : result.m_zones)
  {
    auto const transitions = r.Read(2);
    auto const adjustments = r.Read(2);
    Require(transitions > 0);
    for (size_t i = 0; i < transitions; ++i)
    {
      Transition t{static_cast<int64_t>(r.Read(8)), static_cast<int32_t>(r.Read(4))};
      Require(t.m_offset >= -50400 && t.m_offset <= 50400);
      Require(i == 0 ? t.m_utc == result.m_validFrom : t.m_utc > zone.m_transitions.back().m_utc);
      Require(t.m_utc < result.m_validUntil);
      zone.m_transitions.push_back(t);
    }
    for (size_t i = 0; i < adjustments; ++i)
    {
      Adjustment a{static_cast<int32_t>(r.Read(4)), static_cast<uint8_t>(r.Read(1))};
      Require(a.m_factor >= 32 && a.m_localDay >= 0 && a.m_localDay <= 50000);
      Require(i == 0 || a.m_localDay > zone.m_adjustments.back().m_localDay);
      zone.m_adjustments.push_back(a);
    }
  }
  uint64_t key = 0;
  for (uint32_t i = 0; i < result.m_segments; ++i)
  {
    auto const offset = r.Pos();
    auto const delta = r.VarUint();
    uint64_t next = delta;
    if (i % kBlockSize != 0)
    {
      Require(delta > 0 && delta <= std::numeric_limits<uint64_t>::max() - key);
      next = key + delta;
    }
    Require(i == 0 || next > key);
    key = next;
    if (i % kBlockSize == 0)
      result.m_blocks.push_back({key, offset});
    Require(r.Read(2) < profiles && r.Read(1) < zones && r.Read(1) >= 32);
  }
  Require(r.Pos() == bytes.size() - 4);
  result.m_bytes = std::move(bytes);
  return result;
}

std::optional<double> HistoricalTraffic::GetSpeedKMpH(uint64_t key, int64_t utc) const
{
  if (utc < m_validFrom || utc >= m_validUntil || m_blocks.empty())
    return {};
  auto block =
      std::upper_bound(m_blocks.begin(), m_blocks.end(), key, [](uint64_t k, Block const & b) { return k < b.m_key; });
  if (block == m_blocks.begin())
    return {};
  --block;
  Cursor r(m_bytes, block->m_offset);
  uint64_t current = 0;
  auto const count = std::min(kBlockSize, m_segments - static_cast<uint32_t>(block - m_blocks.begin()) * kBlockSize);
  for (uint32_t i = 0; i < count; ++i)
  {
    current += r.VarUint();
    auto const profile = r.Read(2);
    auto const zoneId = r.Read(1);
    auto const factor = r.Read(1);
    if (current > key)
      break;
    if (current != key)
      continue;
    auto const & zone = m_zones[zoneId];
    auto t = std::upper_bound(zone.m_transitions.begin(), zone.m_transitions.end(), utc,
                              [](int64_t time, Transition const & transition) { return time < transition.m_utc; });
    auto const local = utc + (--t)->m_offset;
    auto const day = static_cast<int32_t>(local / 86400);
    auto const second = local % 86400;
    auto const hour = ((day + 3) % 7) * 24 + second / 3600;  // Monday = 0; epoch was Thursday.
    auto const a = m_bytes[m_profilesOffset + profile * 168 + hour];
    auto const b = m_bytes[m_profilesOffset + profile * 168 + (hour + 1) % 168];
    if (a == 0 || b == 0)
      return {};
    double speed = (a + (b - double(a)) * (second % 3600) / 3600.0) * factor / 128.0;
    auto adjustment = std::lower_bound(zone.m_adjustments.begin(), zone.m_adjustments.end(), day,
                                       [](Adjustment const & value, int32_t d) { return value.m_localDay < d; });
    if (adjustment != zone.m_adjustments.end() && adjustment->m_localDay == day)
      speed *= adjustment->m_factor / 128.0;
    return std::clamp(speed, 1.0, 200.0);
  }
  return {};
}

size_t HistoricalTraffic::GetMemorySize() const
{
  size_t size = sizeof(*this) + m_bytes.capacity() + m_blocks.capacity() * sizeof(Block) +
                m_zones.capacity() * sizeof(Zone) + m_source.capacity();
  for (auto const & z : m_zones)
    size += z.m_transitions.capacity() * sizeof(Transition) + z.m_adjustments.capacity() * sizeof(Adjustment);
  return size;
}
}  // namespace traffic
