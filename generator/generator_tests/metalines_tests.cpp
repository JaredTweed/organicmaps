#include "testing/testing.hpp"

#include "generator/generator_tests/common.hpp"
#include "generator/metalines_builder.hpp"
#include "generator/osm2type.hpp"
#include "generator/osm_element.hpp"

#include "indexer/classificator_loader.hpp"

#include "platform/platform.hpp"

#include "coding/read_write_utils.hpp"

#include "base/scope_guard.hpp"

#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace metalines_tests
{
using namespace feature;

OsmElement MakeHighway(uint64_t id, std::string const & name, std::vector<uint64_t> const & nodes,
                       bool isOneway = false)
{
  OsmElement element;
  element.m_id = id;
  element.m_type = OsmElement::EntityType::Way;
  element.AddTag("ref", "");
  element.AddTag("name", name);
  element.AddTag("highway", "primary");
  if (isOneway)
    element.AddTag("oneway", "yes");
  element.m_nodes = nodes;
  return element;
}

feature::FeatureBuilder MakeFbForTest(OsmElement element)
{
  feature::FeatureBuilder result;
  ftype::GetNameAndType(&element, result.GetParams());
  result.SetLinear();
  return result;
}

MetalineKey MakeKey(OsmElement const & element)
{
  auto const name = element.GetTag("name");
  auto const ref = element.GetTag("ref");
  return {MetalineKind::Named, name, ref};
}

LineStringMerger::InputData MakeInputData(std::vector<OsmElement> const & elements)
{
  LineStringMerger::InputData inputData;
  for (auto const & element : elements)
    inputData[MakeKey(element)].push_back(std::make_shared<LineString>(element));

  return inputData;
}

bool IsEqual(LineStringMerger::LinePtr const & lineString, std::vector<int32_t> const & ways)
{
  auto const & w = lineString->GetWays();
  return w == ways;
}

auto const w1 = MakeHighway(1 /* id */, "w" /* name */, {1, 2, 3} /* nodes */);
auto const w2 = MakeHighway(2 /* id */, "w" /* name */, {3, 4, 5} /* nodes */);
auto const w3 = MakeHighway(3 /* id */, "w" /* name */, {5, 6, 7} /* nodes */);

auto const w4 = MakeHighway(4 /* id */, "w" /* name */, {7, 8, 9} /* nodes */);
auto const w5 = MakeHighway(5 /* id */, "w" /* name */, {9, 10, 11} /* nodes */);

auto const wo6 = MakeHighway(6 /* id */, "w" /* name */, {13, 12, 3} /* nodes */, true /* isOneway */);
auto const wo7 = MakeHighway(7 /* id */, "w" /* name */, {15, 14, 13} /* nodes */, true /* isOneway */);
auto const wo8 = MakeHighway(8 /* id */, "w" /* name */, {17, 16, 15} /* nodes */, true /* isOneway */);

auto const b1 = MakeHighway(1 /* id */, "b" /* name */, {1, 2, 3} /* nodes */);
auto const b2 = MakeHighway(2 /* id */, "b" /* name */, {3, 4, 5} /* nodes */);

UNIT_TEST(MetalinesTest_Case0)
{
  auto const inputData = MakeInputData({w1});
  auto outputData = LineStringMerger::Merge(inputData);
  TEST_EQUAL(outputData.size(), 0 /* unique names roads count */, ());

  outputData = LineStringMerger::Merge({});
  TEST_EQUAL(outputData.size(), 0 /* unique names roads count */, ());
}

UNIT_TEST(MetalinesTest_KeyNamespaces)
{
  // Connected geometry must not join different key kinds or name/ref pairs.
  LineStringMerger::InputData input;
  input[{MetalineKind::Lane, "", ""}].push_back(std::make_shared<LineString>(w1));
  input[{MetalineKind::SharedLane, "", ""}].push_back(std::make_shared<LineString>(w2));
  input[{MetalineKind::Named, "", ""}].push_back(std::make_shared<LineString>(w3));
  TEST(LineStringMerger::Merge(input).empty(), ());

  input.clear();
  input[{MetalineKind::Named, "ab", "c"}].push_back(std::make_shared<LineString>(w1));
  input[{MetalineKind::Named, "a", "bc"}].push_back(std::make_shared<LineString>(w2));
  TEST(LineStringMerger::Merge(input).empty(), ());
}

UNIT_TEST(MetalinesTest_Case1)
{
  auto const inputData = MakeInputData({w1, w2});
  auto const outputData = LineStringMerger::Merge(inputData);

  auto const key = MakeKey(w1);
  TEST_EQUAL(outputData.size(), 1 /* unique names roads count */, ());
  TEST_EQUAL(outputData.at(key)[0]->GetWays().size(), 2 /* merged way size */, ());
  TEST(IsEqual(outputData.at(key)[0], {1, 2}) /* merged way */, ());
}

UNIT_TEST(MetalinesTest_Case2)
{
  auto const inputData = MakeInputData({w1, w3, w2});
  auto const outputData = LineStringMerger::Merge(inputData);

  auto const key = MakeKey(w1);
  TEST_EQUAL(outputData.size(), 1 /* unique names roads count */, ());
  TEST_EQUAL(outputData.at(key)[0]->GetWays().size(), 3 /* merged way size */, ());
  TEST(IsEqual(outputData.at(key)[0], {1, 2, 3}) /* merged way */, ());
}

UNIT_TEST(MetalinesTest_Case3)
{
  auto const inputData = MakeInputData({
      w1,
      w4,
      w2,
      w5,
  });
  auto const outputData = LineStringMerger::Merge(inputData);

  auto const key = MakeKey(w1);
  TEST_EQUAL(outputData.size(), 1 /* unique names roads count */, ());
  TEST_EQUAL(outputData.at(key).size(), 2 /* ways count */, ());

  TEST_EQUAL(outputData.at(key)[0]->GetWays().size(), 2 /* merged way size  */, ());
  TEST(IsEqual(outputData.at(key)[0], {1, 2}) /* merged way */, ());

  TEST_EQUAL(outputData.at(key)[1]->GetWays().size(), 2 /* merged way size  */, ());
  TEST(IsEqual(outputData.at(key)[1], {4, 5}) /* merged way */, ());
}

UNIT_TEST(MetalinesTest_Case4)
{
  auto const inputData = MakeInputData({
      w1,
      wo6,
  });
  auto const outputData = LineStringMerger::Merge(inputData);

  auto const key = MakeKey(w1);
  TEST_EQUAL(outputData.size(), 1 /* unique names roads count */, ());
  TEST_EQUAL(outputData.at(key).size(), 1 /* ways count */, ());
  TEST(IsEqual(outputData.at(key)[0], {6, -1}) /* merged way */, ());
}

UNIT_TEST(MetalinesTest_Case5)
{
  auto const inputData = MakeInputData({
      w1,
      w2,
      wo6,
  });
  auto const outputData = LineStringMerger::Merge(inputData);

  // Node 3 has three incident ways with the same name. Do not choose an
  // arbitrary continuation through the branch.
  TEST_EQUAL(outputData.size(), 0 /* unique names roads count */, ());
}

UNIT_TEST(MetalinesTest_Case6)
{
  auto const inputData = MakeInputData({
      w1,
      b1,
      w2,
      b2,
  });
  auto const outputData = LineStringMerger::Merge(inputData);

  auto const keyW = MakeKey(w1);
  auto const keyB = MakeKey(b1);
  TEST_EQUAL(outputData.size(), 2 /* unique names roads count */, ());
  TEST_EQUAL(outputData.at(keyW).size(), 1 /* ways count */, ());
  TEST_EQUAL(outputData.at(keyB).size(), 1 /* ways count */, ());
}

UNIT_TEST(MetalinesTest_MetalinesBuilderMerge)
{
  classificator::Load();
  auto const filename = generator_tests::GetFileName();
  SCOPE_GUARD(_, std::bind(Platform::RemoveFileIfExists, std::cref(filename)));

  auto c1 = std::make_shared<MetalinesBuilder>(filename);
  auto c2 = c1->Clone();
  c1->CollectFeature(MakeFbForTest(w1), w1);
  c2->CollectFeature(MakeFbForTest(w2), w2);
  c1->CollectFeature(MakeFbForTest(w5), w5);
  c2->CollectFeature(MakeFbForTest(w4), w4);
  c1->Finish();
  c2->Finish();
  c1->Merge(*c2);
  c1->Finalize();

  FileReader reader(filename);
  ReaderSource<FileReader> src(reader);
  std::set<std::vector<int32_t>> s;
  while (src.Size() > 0)
  {
    std::vector<int32_t> ways;
    rw::ReadVectorOfPOD(src, ways);
    s.emplace(std::move(ways));
  }

  TEST_EQUAL(s.size(), 2, ());
  TEST_EQUAL(s.count({1, 2}), 1, ());
  TEST_EQUAL(s.count({4, 5}), 1, ());
}

UNIT_TEST(MetalinesTest_CollectorKeyRoundTrip)
{
  classificator::Load();
  auto const filename = generator_tests::GetFileName();
  SCOPE_GUARD(_, std::bind(Platform::RemoveFileIfExists, std::cref(filename)));
  MetalinesBuilder collector(filename);
  for (uint64_t id = 1; id <= 6; ++id)
  {
    auto way =
        MakeHighway(id, id > 4 ? "named" : "", id % 2 ? std::vector<uint64_t>{1, 2} : std::vector<uint64_t>{2, 3});
    if (id <= 4)
      way.AddTag("cycleway", id <= 2 ? "lane" : "shared_lane");
    collector.CollectFeature(MakeFbForTest(way), way);
  }
  collector.Finish();
  collector.Finalize();
  FileReader reader(filename);
  ReaderSource src(reader);
  std::set<std::vector<int32_t>> chains;
  while (src.Size() > 0)
  {
    std::vector<int32_t> ways;
    rw::ReadVectorOfPOD(src, ways);
    chains.insert(std::move(ways));
  }
  TEST_EQUAL(chains.size(), 3, ());
  TEST_EQUAL(chains.count({1, 2}), 1, ());
  TEST_EQUAL(chains.count({3, 4}), 1, ());
  TEST_EQUAL(chains.count({5, 6}), 1, ());
}
}  // namespace metalines_tests
