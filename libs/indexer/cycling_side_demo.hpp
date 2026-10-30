#pragma once

#include <algorithm>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

// Local visual prototype only. FMD_TEST_ID carries this payload in the demo
// map; it is not a proposal for a production metadata schema or routing API.
namespace cycling_demo
{
enum class Kind : char { None = '0', Track = 't', Lane = 'l', Shared = 's' };
enum class Direction : char { Unknown = '0', Forward = 'f', Backward = 'r', Both = 'b' };
struct Side
{
  Kind m_kind = Kind::None;
  Direction m_direction = Direction::Unknown;
};
struct Sides
{
  Side m_left, m_right;

  void Reverse()
  {
    std::swap(m_left, m_right);
    for (auto * side : {&m_left, &m_right})
    {
      if (side->m_direction == Direction::Forward)
        side->m_direction = Direction::Backward;
      else if (side->m_direction == Direction::Backward)
        side->m_direction = Direction::Forward;
    }
  }
};
inline std::string_view constexpr kPrefix = "offset-bike-v1:";

inline std::string Encode(Sides const & sides)
{
  return std::string(kPrefix) + static_cast<char>(sides.m_left.m_kind) +
         static_cast<char>(sides.m_left.m_direction) + static_cast<char>(sides.m_right.m_kind) +
         static_cast<char>(sides.m_right.m_direction);
}

inline std::optional<Sides> Decode(std::string_view value)
{
  if (!value.starts_with(kPrefix) || value.size() != kPrefix.size() + 4)
    return {};
  value.remove_prefix(kPrefix.size());
  for (size_t i = 0; i < 4; i += 2)
    if (std::string_view("0tls").find(value[i]) == std::string_view::npos ||
        std::string_view("0frb").find(value[i + 1]) == std::string_view::npos)
      return {};
  return Sides{{static_cast<Kind>(value[0]), static_cast<Direction>(value[1])},
               {static_cast<Kind>(value[2]), static_cast<Direction>(value[3])}};
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
  auto const negative = [](std::string_view value)
  { return value == "no" || value == "none" || value == "false"; };
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
        if (positive(tag(prefix + ":" + edge)) &&
            (mode == "motor_vehicle" || mode == "motorcar" || mode == "vehicle"))
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
  if (reversed)
    result.Reverse();
  return result;
}
}  // namespace cycling_demo
