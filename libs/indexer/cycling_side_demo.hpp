#pragma once

#include "base/string_utils.hpp"
#include "geometry/point2d.hpp"

#include <algorithm>
#include <cmath>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

// Local visual prototype only. FMD_TEST_ID carries this payload in the demo
// map; it is not a proposal for a production metadata schema or routing API.
namespace cycling_demo
{
enum class Kind : char
{
  None = '0',
  Track = 't',
  Lane = 'l',
  Shared = 's'
};
enum class Direction : char
{
  Unknown = '0',
  Forward = 'f',
  Backward = 'r',
  Both = 'b'
};
struct Side
{
  Kind m_kind = Kind::None;
  Direction m_direction = Direction::Unknown;
  std::vector<m2::PointD> m_junctions;
};
struct Sides
{
  Side m_left, m_right;

  void Reverse()
  {
    std::swap(m_left, m_right);
    for (auto * side : {&m_left, &m_right})
      if (side->m_direction == Direction::Forward)
        side->m_direction = Direction::Backward;
      else if (side->m_direction == Direction::Backward)
        side->m_direction = Direction::Forward;
  }
};
inline std::string_view constexpr kPrefix = "offset-bike-v1:";
inline std::string_view constexpr kJunctionPrefix = "offset-bike-v2:";

inline std::optional<std::vector<m2::PointD>> ReadJunctions(std::string_view text)
{
  std::vector<m2::PointD> result;
  while (!text.empty())
  {
    auto const end = text.find(';');
    auto const pair = text.substr(0, end);
    auto const comma = pair.find(',');
    double x, y;
    if (comma == std::string_view::npos || !strings::to_double(pair.substr(0, comma), x) ||
        !strings::to_double(pair.substr(comma + 1), y) || !std::isfinite(x) || !std::isfinite(y) || std::abs(x) > 180 ||
        std::abs(y) > 180 || result.size() == 64)
      return {};
    result.emplace_back(x, y);
    if (end == std::string_view::npos)
      break;
    text.remove_prefix(end + 1);
    if (text.empty())
      return {};
  }
  return result;
}

inline std::string Encode(Sides const & sides)
{
  bool const junctions = !sides.m_left.m_junctions.empty() || !sides.m_right.m_junctions.empty();
  auto result = std::string(junctions ? kJunctionPrefix : kPrefix) + static_cast<char>(sides.m_left.m_kind) +
                static_cast<char>(sides.m_left.m_direction) + static_cast<char>(sides.m_right.m_kind) +
                static_cast<char>(sides.m_right.m_direction);
  if (junctions)
    for (auto const * side : {&sides.m_left, &sides.m_right})
    {
      result += '|';
      for (size_t i = 0; i < side->m_junctions.size(); ++i)
      {
        if (i != 0)
          result += ';';
        auto const & p = side->m_junctions[i];
        result += strings::to_string_dac(p.x, 9) + ',' + strings::to_string_dac(p.y, 9);
      }
    }
  return result;
}

inline std::optional<Sides> Decode(std::string_view value)
{
  bool const junctions = value.starts_with(kJunctionPrefix);
  auto const prefix = junctions ? kJunctionPrefix : kPrefix;
  if (!value.starts_with(prefix) || value.size() < prefix.size() + 4)
    return {};
  value.remove_prefix(prefix.size());
  if ((!junctions && value.size() != 4) || (junctions && (value.size() < 6 || value[4] != '|')))
    return {};
  for (size_t i = 0; i < 4; i += 2)
    if (std::string_view("0tls").find(value[i]) == std::string_view::npos ||
        std::string_view("0frb").find(value[i + 1]) == std::string_view::npos)
      return {};
  Sides result{{static_cast<Kind>(value[0]), static_cast<Direction>(value[1])},
               {static_cast<Kind>(value[2]), static_cast<Direction>(value[3])}};
  if (junctions)
  {
    value.remove_prefix(5);
    auto const divider = value.find('|');
    if (divider == std::string_view::npos)
      return {};
    auto left = ReadJunctions(value.substr(0, divider));
    auto right = ReadJunctions(value.substr(divider + 1));
    if (!left || !right)
      return {};
    result.m_left.m_junctions = std::move(*left);
    result.m_right.m_junctions = std::move(*right);
  }
  return result;
}

inline char const * TypeName(Kind kind)
{
  switch (kind)
  {
  case Kind::Track: return "track";
  case Kind::Lane: return "lane";
  case Kind::Shared: return "shared_lane";
  case Kind::None: return "";
  }
  return "";
}

template <typename GetTag>
std::optional<Sides> ReadSides(GetTag const & tag, bool reversed)
{
  auto const negative = [](std::string_view value) { return value == "no" || value == "none" || value == "false"; };
  auto const protectedFromTraffic = [&](std::string const & key)
  {
    for (std::string const kind : {"separation", "barrier"})
    {
      auto const positive = [&](std::string const & value)
      {
        return !value.empty() && !negative(value) && value != "no_separation" &&
               (kind != "separation" || (value != "studs" && value != "cone"));
      };
      std::string const prefix = key + ":" + kind;
      if (positive(tag(prefix)) || positive(tag(prefix + ":both")))
        return true;
      for (std::string const edge : {"left", "right"})
      {
        auto const mode = tag(key + ":traffic_mode:" + edge);
        if (positive(tag(prefix + ":" + edge)) && (mode == "motor_vehicle" || mode == "motorcar" || mode == "vehicle"))
          return true;
      }
    }
    return false;
  };
  auto const read = [&](std::string const & key, std::optional<Side> fallback) -> std::optional<Side>
  {
    auto const value = tag(key);
    auto const lane = tag(key + ":lane");
    Side side = value.empty() && lane.empty() ? fallback.value_or(Side{}) : Side{};
    if (negative(value) || value == "separate" || value == "use_sidepath")
      return side;
    if (value == "track" || value == "opposite_track" || value == "protected_lane")
      side.m_kind = Kind::Track;
    else if (value == "lane" || value == "opposite_lane" || value == "buffered_lane" || lane == "exclusive")
      side.m_kind = Kind::Lane;
    else if (value == "shared_lane" || value == "share_busway" || value == "opposite_share_busway" ||
             value == "shoulder")
      side.m_kind = Kind::Shared;
    if (lane == "advisory" || lane == "pictogram")
      side.m_kind = Kind::Shared;
    if (side.m_kind == Kind::None)
      return {};
    if (side.m_kind == Kind::Lane && protectedFromTraffic(key))
      side.m_kind = Kind::Track;
    auto const oneway = tag(key + ":oneway");
    if (oneway == "yes" || oneway == "1" || oneway == "true")
      side.m_direction = Direction::Forward;
    else if (oneway == "-1" || value.starts_with("opposite_"))
      side.m_direction = Direction::Backward;
    else if (negative(oneway))
      side.m_direction = Direction::Both;
    return side;
  };
  auto const both = read("cycleway:both", {});
  auto const left = read("cycleway:left", both);
  auto const right = read("cycleway:right", both);
  if (!both && !left && !right)
    return {};  // Do not invent sides from an unqualified centerline category.
  Sides result{left.value_or(both.value_or(Side{})), right.value_or(both.value_or(Side{}))};
  // These debug-only tags are produced from shared OSM node identities by the
  // fixture preprocessor, never from geometric endpoint proximity.
  auto leftJunctions = ReadJunctions(tag("om:demo:cycle_junctions:left"));
  auto rightJunctions = ReadJunctions(tag("om:demo:cycle_junctions:right"));
  if (leftJunctions)
    result.m_left.m_junctions = std::move(*leftJunctions);
  if (rightJunctions)
    result.m_right.m_junctions = std::move(*rightJunctions);
  if (reversed)
    result.Reverse();
  return result;
}
}  // namespace cycling_demo
