#include "testing/testing.hpp"

#include "routing/routing_callbacks.hpp"
#include "routing/routing_integration_tests/generated_map_test.hpp"
#include "routing/routing_integration_tests/routing_test_tools.hpp"

#include "platform/platform_tests_support/scoped_file.hpp"

#include "geometry/mercator.hpp"

#include "pugixml.hpp"

#include <initializer_list>
#include <iostream>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace
{
using Tags = std::vector<std::pair<std::string, std::string>>;

std::string MakeNetwork(Tags const & shortcutTags)
{
  pugi::xml_document document;
  auto osm = document.append_child("osm");
  osm.append_attribute("version") = "0.6";
  struct Node
  {
    int id;
    double lat, lon;
  };
  for (auto const & node : {Node{1, 55.075, 82.935}, Node{2, 55.075, 82.939}, Node{3, 55.075, 82.941},
                            Node{4, 55.075, 82.945}, Node{5, 55.085, 82.939}, Node{6, 55.085, 82.941}})
  {
    auto element = osm.append_child("node");
    element.append_attribute("id") = node.id;
    element.append_attribute("lat") = node.lat;
    element.append_attribute("lon") = node.lon;
  }
  auto const addWay = [&](int id, std::initializer_list<int> nodes, Tags const & tags)
  {
    auto way = osm.append_child("way");
    way.append_attribute("id") = id;
    for (int node : nodes)
      way.append_child("nd").append_attribute("ref") = node;
    for (auto const & [key, value] : tags)
    {
      auto tag = way.append_child("tag");
      tag.append_attribute("k") = key.c_str();
      tag.append_attribute("v") = value.c_str();
    }
  };
  Tags const road = {{"highway", "residential"}, {"surface", "asphalt"}};
  addWay(10, {1, 2}, road);
  addWay(20, {2, 3}, shortcutTags);
  addWay(30, {3, 4}, road);
  addWay(40, {2, 5, 6, 3}, road);
  std::ostringstream output;
  document.save(output);
  return output.str();
}

void CheckRoutes(Tags const & tags, routing::VehicleType vehicle, bool forwardShortcut, bool reverseShortcut)
{
  platform::tests_support::ScopedFile fixture("cycling-readiness.osm", MakeNetwork(tags));
  integration::GeneratedMapTest map(fixture.GetFullPath(), "Russia_Novosibirsk Oblast", vehicle);
  auto const west = mercator::FromLatLon(55.075, 82.935);
  auto const east = mercator::FromLatLon(55.075, 82.945);
  for (bool reverse : {false, true})
  {
    auto const route =
        integration::CalculateRoute(map.GetComponents(), reverse ? east : west, {0, 0}, reverse ? west : east);
    TEST_EQUAL(route.second, routing::RouterResultCode::NoError, (tags, vehicle, reverse));
    TEST(route.first, (tags, vehicle, reverse));
    auto const used = map.GetUsedOsmWays(*route.first);
    bool const expected = reverse ? reverseShortcut : forwardShortcut;
    TEST_EQUAL(used.count(20) != 0, expected, (tags, vehicle, reverse, used));
    TEST_EQUAL(used.count(40) != 0, !expected, (tags, vehicle, reverse, used));
    std::cout << "READINESS_ROUTE vehicle=" << static_cast<int>(vehicle) << " reverse=" << reverse
              << " shortcut=" << expected << " ways=";
    for (auto const id : used)
      std::cout << id << ',';
    std::cout << '\n';
  }
}
}  // namespace

UNIT_TEST(CyclingReadiness_PermissiveMotorAccess)
{
  for (auto const highway : {"pedestrian", "footway", "path", "cycleway"})
  {
    for (auto const value : {"yes", "designated", "permissive", "no", "private"})
    {
      Tags tags = {{"highway", highway}, {"surface", "asphalt"}, {"motor_vehicle", value}};
      bool const allowed = std::string(value) != "no" && std::string(value) != "private";
      CheckRoutes(tags, routing::VehicleType::Car, allowed, allowed);
    }
    Tags const noPermission = {{"highway", highway}, {"surface", "asphalt"}};
    CheckRoutes(noPermission, routing::VehicleType::Car, false, false);
    for (bool reverseOrder : {false, true})
    {
      Tags tags = {{"highway", highway}, {"surface", "asphalt"}};
      if (reverseOrder)
        tags.emplace_back("motorcar", "no");
      tags.emplace_back("motor_vehicle", "permissive");
      if (!reverseOrder)
        tags.emplace_back("motorcar", "no");
      CheckRoutes(tags, routing::VehicleType::Car, false, false);
    }
  }
}

UNIT_TEST(CyclingReadiness_BicycleDirectionAndAccess)
{
  using routing::VehicleType;
  Tags const road = {{"highway", "residential"}, {"surface", "asphalt"}};
  auto check = [&](Tags extra, bool forward, bool reverse)
  {
    Tags tags = road;
    tags.insert(tags.end(), extra.begin(), extra.end());
    CheckRoutes(tags, VehicleType::Bicycle, forward, reverse);
  };
  check({}, true, true);
  check({{"cycleway", "lane"}}, true, true);
  check({{"cycleway", "shared_lane"}}, true, true);
  check({{"cycleway", "track"}}, true, true);
  check({{"oneway", "yes"}}, true, false);
  check({{"oneway", "yes"}, {"oneway:bicycle", "no"}}, true, true);
  check({{"oneway", "yes"}, {"cycleway", "opposite_lane"}}, true, true);
  check({{"oneway", "-1"}}, false, true);
  check({{"oneway:bicycle", "yes"}}, true, false);
  check({{"bicycle", "no"}}, false, false);
}

UNIT_TEST(CyclingReadiness_PedestrianStillAllowed)
{
  for (auto const highway : {"pedestrian", "footway"})
    CheckRoutes({{"highway", highway}, {"surface", "asphalt"}, {"foot", "yes"}, {"motor_vehicle", "permissive"}},
                routing::VehicleType::Pedestrian, true, true);
}
