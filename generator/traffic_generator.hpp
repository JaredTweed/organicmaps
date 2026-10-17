#pragma once

#include <string>

namespace traffic
{
// Export exact directed segment geometry for offline provider map matching. Does not modify the map.
bool ExportHistoricalTrafficSegments(std::string const & mwmPath, std::string const & output);
bool GenerateTrafficKeysFromDataFile(std::string const & mwmPath);
}  // namespace traffic
