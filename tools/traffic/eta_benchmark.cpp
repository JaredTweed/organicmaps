#include "routing/edge_estimator.hpp"
#include "routing/geometry.hpp"
#include "routing_common/maxspeed_conversion.hpp"
#include "traffic/historical_traffic.hpp"

#include <chrono>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>

// Actual CarEstimator overhead on synthetic geometry; excludes route search and cold map hashing.
int main(int argc, char ** argv)
{
  if (argc != 2)
    return 1;
  std::ifstream input(argv[1], std::ios::binary);
  auto const package = traffic::HistoricalTraffic::Deserialize({std::istreambuf_iterator<char>(input), {}}, "Benchmark",
                                                               1767225600, 12345, "AAAAAAAAAAAA");
  auto const estimator =
      routing::EdgeEstimator::Create(routing::VehicleType::Car, 200, {1.0, 1.0}, nullptr, nullptr, nullptr);
  routing::RoadGeometry const road(false, routing::Maxspeed(measurement_utils::Units::Metric, 60, 60),
                                   routing::RoadGeometry::Points({{0.0, 0.0}, {0.0, 0.001}}));
  auto run = [&]
  {
    double time = 0;
    auto const start = std::chrono::steady_clock::now();
    for (uint32_t i = 0; i < 100000; ++i)
    {
      auto const id = (uint64_t(i) * 999983) % 1000000;
      estimator->SetHistoricalTrafficTime(1767618000 + static_cast<int64_t>(time));
      time += estimator->CalcSegmentWeight(routing::Segment(0, id / 2, 0, id % 2 == 0), road,
                                           routing::EdgeEstimator::Purpose::ETA);
    }
    std::cout << "elapsed_ms="
              << std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count()
              << " synthetic_eta_seconds=" << time << '\n';
  };
  std::cout << "baseline ";
  run();
  estimator->SetHistoricalTraffic([&](routing::Segment const & segment, int64_t utc)
  {
    return package.GetSpeedKMpH(
        traffic::HistoricalTraffic::SegmentKey(segment.GetFeatureId(), segment.GetSegmentIdx(), segment.IsForward()),
        utc);
  });
  std::cout << "historical ";
  run();
}
