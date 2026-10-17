project(traffic)

set(SRC
  speed_groups.cpp
  speed_groups.hpp
  traffic_cache.cpp
  traffic_cache.hpp
  traffic_info.cpp
  traffic_info.hpp
)

omim_add_library(historical_traffic historical_traffic.cpp historical_traffic.hpp)
omim_add_library(${PROJECT_NAME} ${SRC})

target_link_libraries(${PROJECT_NAME}
  PUBLIC
    historical_traffic
    routing_common
    indexer
)

omim_add_test_subdirectory(traffic_tests)

if (BUILD_TESTING)
  add_test(NAME historical_traffic_generator_tests
    COMMAND Python3::Interpreter -m unittest discover -s ${OMIM_ROOT}/tools/traffic)
  set_tests_properties(historical_traffic_generator_tests PROPERTIES LABELS "omim-test")
  omim_add_test(historical_traffic_tests traffic_tests/historical_traffic_test.cpp NO_PLATFORM_INIT)
  target_link_libraries(historical_traffic_tests PRIVATE historical_traffic)
  omim_add_executable(historical_traffic_benchmark ../../tools/traffic/benchmark.cpp)
  target_link_libraries(historical_traffic_benchmark PRIVATE historical_traffic)
endif()
