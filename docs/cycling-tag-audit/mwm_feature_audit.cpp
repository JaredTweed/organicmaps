#include "coding/files_container.hpp"
#include "defines.hpp"
#include "drape_frontend/metaline_data.hpp"
#include "generator/utils.hpp"
#include "indexer/classificator.hpp"
#include "indexer/classificator_loader.hpp"
#include "indexer/feature.hpp"
#include "indexer/feature_processor.hpp"
#include "platform/platform.hpp"

#include <glaze/json.hpp>

#include <algorithm>
#include <array>
#include <iostream>
#include <map>
#include <string>
#include <vector>

struct AuditFeature
{
  std::string kind = "feature";
  uint32_t id = 0;
  std::vector<uint64_t> osm_ids;
  int geometry_type = 0;
  int layer = 0;
  int rank = 0;
  std::vector<std::vector<std::string>> types;
  std::vector<std::pair<int, std::string>> names;
  std::string ref;
  std::string house_number;
  std::map<int, std::vector<uint8_t>> metadata;
  std::vector<std::array<double, 2>> points;
};

struct AuditChain
{
  std::string kind = "chain";
  std::vector<uint32_t> features;
  std::vector<bool> reversed;
  std::vector<double> offsets;
};

struct AuditMetadata
{
  std::string kind = "metadata";
  std::map<std::string, std::string> classifier_paths;
  std::map<std::string, uint64_t> sections;
  int metalines_version = -1;
  bool offsets_present = false;
  bool offsets_applied = false;
};

template <typename T>
void Emit(T const & value)
{
  std::string json;
  CHECK(!glz::write_json(value, json), ());
  std::cout << json << '\n';
}

int main(int argc, char ** argv)
{
  if (argc != 4)
  {
    std::cerr << "Usage: mwm_feature_audit RESOURCE_DIR MAP OSM2FT\n";
    return 2;
  }
  GetPlatform().SetResourceDir(argv[1]);
  // Writable files take precedence over resources in Platform::GetReader.
  // Never inherit an unrelated ./data classifier from the launch directory.
  GetPlatform().SetWritableDirForTests(argv[1]);
  // Export type data only; drawing-rule loading belongs to the native capture.
  auto const readText = [](char const * name)
  {
    auto reader = GetPlatform().GetReader(name);
    std::string text(reader->Size(), '\0');
    reader->Read(0, text.data(), text.size());
    return text;
  };
  classificator::LoadTypes(readText("classificator.txt"), readText("types.txt"));
  std::map<uint32_t, std::vector<uint64_t>> reverse;
  CHECK(generator::ForEachOsmId2FeatureId(argv[3],
                                          [&](generator::CompositeId const & osmId, uint32_t id)
  {
    for (auto sourceId : {osmId.m_mainId, osmId.m_additionalId})
      if (sourceId.GetEncodedId() != base::GeoObjectId::kInvalid)
        reverse[id].push_back(sourceId.GetEncodedId());
  }),
        ("Cannot load complete source identity mapping"));
  for (auto & [id, sources] : reverse)
  {
    std::sort(sources.begin(), sources.end());
    sources.erase(std::unique(sources.begin(), sources.end()), sources.end());
  }

  FilesContainerR container(argv[2]);
  AuditMetadata metadata;
  for (auto const * name : {"classificator.txt", "types.txt"})
    metadata.classifier_paths[name] = GetPlatform().ReadPathForFile(name);
  container.ForEachTagInfo([&](auto const & info) { metadata.sections[info.m_tag] = info.m_size; });
  std::vector<df::detail::MetalineData> chains;
  if (container.IsExist(METALINES_FILE_TAG))
  {
    auto reader = container.GetReader(METALINES_FILE_TAG);
    ReaderSource version(reader);
    metadata.metalines_version = ReadPrimitiveFromSource<uint8_t>(version);
    ReaderSource src(reader);
    chains = df::detail::ReadMetalines(src, MwmSet::MwmId{});
    CHECK_EQUAL(src.Size(), 0, ());
  }
  metadata.offsets_present = container.IsExist(METALINES_OFFSETS_FILE_TAG);
  if (metadata.offsets_present)
  {
    ReaderSource offsets(container.GetReader(METALINES_OFFSETS_FILE_TAG));
    metadata.offsets_applied = df::detail::TryReadMetalineOffsets(offsets, MwmSet::MwmId{}, chains);
    CHECK(metadata.offsets_applied, ("Mismatched optional phase data"));
  }
  Emit(metadata);
  feature::ForEachFeature(argv[2], [&](FeatureType & ft, uint32_t id)
  {
    AuditFeature out;
    out.id = id;
    out.osm_ids = reverse[id];
    out.geometry_type = static_cast<int>(ft.GetGeomType());
    out.layer = ft.GetLayer();
    out.rank = ft.GetRank();
    ft.ForEachType([&](uint32_t type) { out.types.push_back(classif().GetFullObjectNamePath(type)); });
    ft.ForEachName([&](int8_t language, std::string_view name) { out.names.emplace_back(language, name); });
    std::sort(out.names.begin(), out.names.end());
    out.ref = ft.GetRef();
    out.house_number = ft.GetHouseNumber();
    ft.GetMetadata().ForEach([&](auto type, auto const & value)
    { out.metadata[static_cast<int>(type)].assign(value.begin(), value.end()); });
    if (ft.GetGeomType() == feature::GeomType::Area)
    {
      ft.ForEachTriangle([&](auto const & a, auto const & b, auto const & c)
      {
        for (auto const & p : {a, b, c})
          out.points.push_back({p.x, p.y});
      }, FeatureType::BEST_GEOMETRY);
    }
    else
      ft.ForEachPoint([&](auto const & p) { out.points.push_back({p.x, p.y}); }, FeatureType::BEST_GEOMETRY);
    Emit(out);
  });
  for (auto const & chain : chains)
  {
    AuditChain out;
    for (auto const & id : chain.m_features)
    {
      out.features.push_back(id.m_index);
      out.reversed.push_back(chain.m_reversed.count(id) != 0);
    }
    out.offsets = chain.m_dashPhaseOffsets;
    Emit(out);
  }
}
