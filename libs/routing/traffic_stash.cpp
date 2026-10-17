#include "routing/traffic_stash.hpp"

#include "routing/data_source.hpp"

#include "platform/platform.hpp"

#include "coding/blake3.hpp"
#include "coding/file_reader.hpp"

#include "base/checked_cast.hpp"

#include <ctime>
#include <limits>
#include <map>
#include <mutex>
#include <string>
#include <unordered_map>

namespace routing
{
namespace
{
struct MapHashCacheEntry
{
  uint64_t m_size;
  time_t m_mtime;
  std::string m_hash;
};

std::mutex g_mapHashCacheMutex;
std::unordered_map<std::string, MapHashCacheEntry> g_mapHashCache;

std::string GetMapHash(std::string const & path, uint64_t size, platform::CountryFile const & countryFile)
{
  // Storage has already verified downloaded maps and keeps the truncated BLAKE3 digest here.
  if (!countryFile.GetHash().empty())
    return countryFile.GetHash();

  // Bundled or test maps may have no CountryFile hash. Avoid re-reading a large map on every
  // route calculation; the identity is keyed by size and modification time.
  time_t const mtime = Platform::GetFileModificationTime(path);
  {
    std::lock_guard lock(g_mapHashCacheMutex);
    auto const it = g_mapHashCache.find(path);
    if (it != g_mapHashCache.end() && it->second.m_size == size && it->second.m_mtime == mtime)
      return it->second.m_hash;
  }
  auto const hash = coding::Blake3::CalculateMwmBase64(path);
  {
    std::lock_guard lock(g_mapHashCacheMutex);
    if (g_mapHashCache.size() >= 64)
      g_mapHashCache.clear();
    g_mapHashCache[path] = {size, mtime, hash};
  }
  return hash;
}
}  // namespace
TrafficStash::TrafficStash(traffic::TrafficCache const & source, std::shared_ptr<NumMwmIds> numMwmIds)
  : m_source(source)
  , m_numMwmIds(std::move(numMwmIds))
{
  CHECK(m_numMwmIds, ());
}

traffic::SpeedGroup TrafficStash::GetSpeedGroup(Segment const & segment) const
{
  if (segment.GetSegmentIdx() > std::numeric_limits<uint16_t>::max())
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
        try
        {
          FileReader reader(path + ".traffic");
          std::vector<uint8_t> bytes(packageSize);
          reader.Read(0, bytes.data(), bytes.size());
          it->second = traffic::HistoricalTraffic::Deserialize(
              std::move(bytes), value.GetCountryFileName(), value.GetMwmVersion().GetSecondsSinceEpoch(), mapSize,
              GetMapHash(path, mapSize, value.m_file.GetCountryFile()));
        }
        catch (std::exception const &)
        {
          LOG(LWARNING, ("Ignoring invalid historical traffic package for", value.GetCountryFileName()));
        }
      }
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
