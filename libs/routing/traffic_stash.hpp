#pragma once

#include "routing/segment.hpp"

#include "traffic/historical_traffic.hpp"
#include "traffic/traffic_cache.hpp"
#include "traffic/traffic_info.hpp"

#include "routing_common/num_mwm_id.hpp"

#include "indexer/mwm_set.hpp"

#include "base/assert.hpp"

#include <memory>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>

namespace routing
{
class MwmDataSource;
inline constexpr std::string_view kOfflineHistoricalTrafficEnabled = "OfflineHistoricalTrafficEnabled";
class TrafficStash final
{
public:
  class Guard final
  {
  public:
    explicit Guard(std::shared_ptr<TrafficStash> stash) : m_stash(std::move(stash))
    {
      if (m_stash)
        m_stash->CopyTraffic();
    }

    ~Guard()
    {
      if (m_stash)
        m_stash->Clear();
    }

  private:
    std::shared_ptr<TrafficStash> m_stash;
  };

  TrafficStash(traffic::TrafficCache const & source, std::shared_ptr<NumMwmIds> numMwmIds, bool useLiveTraffic = true);

  traffic::SpeedGroup GetSpeedGroup(Segment const & segment) const;
  void SetColoring(NumMwmId numMwmId, std::shared_ptr<traffic::TrafficInfo::Coloring const> coloring);
  bool Has(NumMwmId numMwmId) const;
  std::optional<double> GetHistoricalSpeed(Segment const & segment, int64_t utc, MwmDataSource & dataSource);

private:
  void CopyTraffic();

  void Clear()
  {
    m_mwmToTraffic.clear();
    m_historical.clear();
  }

  // Also caches absent/invalid packages for the duration of one route calculation.
  std::unordered_map<NumMwmId, std::optional<traffic::HistoricalTraffic>> m_historical;
  struct MapIdentity
  {
    std::weak_ptr<MwmInfo> m_info;
    std::string m_hash;
  };
  // Registered maps are immutable. Re-registration supplies a new MwmInfo, even at the same path.
  std::unordered_map<NumMwmId, MapIdentity> m_mapIdentities;
  bool const m_useLiveTraffic;
  traffic::TrafficCache const & m_source;
  std::shared_ptr<NumMwmIds> m_numMwmIds;
  std::unordered_map<NumMwmId, std::shared_ptr<traffic::TrafficInfo::Coloring const>> m_mwmToTraffic;
};
}  // namespace routing
