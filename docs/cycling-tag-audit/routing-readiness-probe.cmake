# Local evidence target only: do not alter the split production sources/CMake.
set(CYCLING_READINESS_DIR "${CMAKE_CURRENT_LIST_DIR}")
function(add_cycling_readiness_probe)
  # Keep this local probe below the laptop's hard memory cap. Assertions stay on.
  foreach(target map kml)
    set_target_properties(${target} PROPERTIES UNITY_BUILD_BATCH_SIZE 2)
    target_compile_options(${target} PRIVATE -g0)
  endforeach()
  omim_add_test(cycling_readiness_probe
    "${CYCLING_READINESS_DIR}/routing_readiness_probe.cpp"
    "${CMAKE_SOURCE_DIR}/libs/routing/routing_integration_tests/generated_map_test.cpp"
    "${CMAKE_SOURCE_DIR}/libs/routing/routing_integration_tests/routing_test_tools.cpp"
  )
  target_link_libraries(cycling_readiness_probe PRIVATE
    generator_tests_support platform_tests_support routing map pugixml
  )
  set_target_properties(cycling_readiness_probe PROPERTIES UNITY_BUILD OFF)
  target_compile_options(cycling_readiness_probe PRIVATE -g0)
endfunction()
cmake_language(DEFER DIRECTORY "${CMAKE_SOURCE_DIR}" CALL add_cycling_readiness_probe)
