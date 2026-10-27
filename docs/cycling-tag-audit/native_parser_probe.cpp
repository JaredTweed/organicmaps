#include "indexer/drules_selector_parser.hpp"

#include <iostream>
#include <stdexcept>
#include <string>

namespace
{
void Require(bool condition)
{
  if (!condition)
    throw std::runtime_error("Selector parser probe failed");
}

void Check(std::string const & input, drule::SelectorOperatorType op, std::string const & value)
{
  drule::SelectorExpression expression;
  Require(drule::ParseSelector(input, expression));
  Require(expression.m_tag == "extra_tag" && expression.m_operator == op && expression.m_value == value);
}
}  // namespace

int main()
{
  using namespace drule;
  Check("extra_tag=cyclewaytag=lane", SelectorOperatorEqual, "cyclewaytag=lane");
  Check("extra_tag!=cyclewaytag=track", SelectorOperatorNotEqual, "cyclewaytag=track");
  Check("extra_tag=highway=path=bicycle", SelectorOperatorEqual, "highway=path=bicycle");
  Check("extra_tag=cycleway:left=lane", SelectorOperatorEqual, "cycleway:left=lane");

  for (auto const * input : {"", "cycleway:left=lane", "extra_tag=", "=lane"})
  {
    SelectorExpression expression;
    Require(!ParseSelector(input, expression));
  }

  size_t generated = 0;
  for (std::string input; std::getline(std::cin, input);)
  {
    SelectorExpression expression;
    Require(ParseSelector(input, expression));
    Require(expression.m_tag == "extra_tag");
    Require(expression.m_operator == SelectorOperatorEqual || expression.m_operator == SelectorOperatorNotEqual);
    ++generated;
  }
  std::cout << "{\"native_parser_cases\":8,\"generated_predicates_parsed\":" << generated << "}\n";
}
