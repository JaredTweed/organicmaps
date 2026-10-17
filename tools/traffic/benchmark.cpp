#include "traffic/historical_traffic.hpp"

#include <chrono>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>

int main(int argc, char ** argv)
{
  if (argc < 2 || argc > 3)
    return 1;
  std::ifstream input(argv[1], std::ios::binary);
  std::vector<uint8_t> bytes{std::istreambuf_iterator<char>(input), {}};
  auto const size = bytes.size();
  auto const begin = std::chrono::steady_clock::now();
  auto const package =
      traffic::HistoricalTraffic::Deserialize(std::move(bytes), "Benchmark", 1767225600, 12345, "AAAAAAAAAAAA");
  auto const loaded = std::chrono::steady_clock::now();
  constexpr uint32_t n = 1000000;
  double total = 0;
  for (uint32_t i = 0; i < n; ++i)
    total += (100.0 + i % 100) / (60.0 / 3.6);
  auto const baseline = std::chrono::steady_clock::now();
  std::cout << "baseline_checksum=" << total << '\n';
  total = 0;
  for (uint32_t i = 0; i < n; ++i)
  {
    // Permutation gives non-sequential random access over one million directed segments.
    uint32_t const id = (uint64_t(i) * 999983) % n;
    auto const speed =
        package.GetSpeedKMpH(traffic::HistoricalTraffic::SegmentKey(id / 2, 0, id % 2 == 0), 1767618000 + i % 3600)
            .value_or(60.0);
    if (argc == 2 && speed != (id % 2 == 0 ? 60.0 : 20.0))
      return 2;
    total += (100.0 + i % 100) / (speed / 3.6);
  }
  auto const adjusted = std::chrono::steady_clock::now();
  auto ms = [](auto a, auto b) { return std::chrono::duration<double, std::milli>(b - a).count(); };
  std::cout << "segments=" << n << " bytes=" << size << " estimated_resident_bytes=" << package.GetMemorySize()
            << " load_ms=" << ms(begin, loaded) << " baseline_ms=" << ms(loaded, baseline)
            << " traffic_ms=" << ms(baseline, adjusted) << " adjusted_checksum=" << total << '\n';
}
