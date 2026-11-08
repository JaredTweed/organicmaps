package app.organicmaps.contacts;

import androidx.annotation.NonNull;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

final class ContactAddress
{
  static final class SearchQuery
  {
    @NonNull
    final String query;
    @NonNull
    final String expectedStreet;
    SearchQuery(@NonNull String query, @NonNull String expectedStreet)
    {
      this.query = query;
      this.expectedStreet = expectedStreet;
    }

    @Override
    public boolean equals(Object object)
    {
      return object instanceof SearchQuery other && query.equals(other.query)
   && expectedStreet.equals(other.expectedStreet);
    }

    @Override
    public int hashCode()
    {
      return 31 * query.hashCode() + expectedStreet.hashCode();
    }

    @Override
    public String toString()
    {
      return query;
    }
  }

  @NonNull
  final String address;
  @NonNull
  final String street;
  @NonNull
  final String locality;
  @NonNull
  final String region;
  @NonNull
  final String country;
  @NonNull
  private final String mNormalizedStreet;
  @NonNull
  private final String mFormattingCountry;
  @NonNull
  private final String mResolutionContext;
  @NonNull
  private final String mAddressKey;
  @NonNull
  private final List<SearchQuery> mSearchQueries;

  ContactAddress(@NonNull String address, @NonNull String street, @NonNull String locality)
  {
    this(address, street, locality, "", "");
  }

  ContactAddress(@NonNull String address, @NonNull String street, @NonNull String locality, @NonNull String region,
                 @NonNull String country)
  {
    this.address = address;
    this.street = street;
    this.locality = locality;
    this.region = region;
    this.country = country;
    mFormattingCountry = ContactAddressNormalizer.formattingCountry(country, address);
    mNormalizedStreet = normalizeStreet();
    mResolutionContext = normalizeResolutionContext();
    mAddressKey =
        (mNormalizedStreet + "|" + mResolutionContext + "|" + region + "|" + country).toLowerCase(Locale.ROOT);
    mSearchQueries = List.copyOf(buildSearchQueries());
  }

  @NonNull
  String getNormalizedStreet()
  {
    return mNormalizedStreet;
  }

  @NonNull
  private String normalizeStreet()
  {
    if (!ContactAddressNormalizer.usesNorthAmericanFormatting(mFormattingCountry))
      return ContactAddressNormalizer.normalizeStreet(street.isEmpty() ? address : street, mFormattingCountry);
    final String firstPart = address.split(",", 2)[0].trim();
    if (street.isEmpty() && ContactAddressNormalizer.looksLikeStructuredStreet(firstPart)
        && !ContactAddressNormalizer.hasRecognizedStreetSuffix(firstPart))
      return firstPart;
    final String formattedStreet = ContactAddressNormalizer.normalizeStreet(address);
    final String structuredStreet = ContactAddressNormalizer.normalizeStreet(street);
    final boolean useFormattedStreet = ContactAddressNormalizer.looksLikeAddressQuery(formattedStreet);
    return useFormattedStreet ? formattedStreet : structuredStreet;
  }

  @NonNull
  List<SearchQuery> getSearchQueries()
  {
    return mSearchQueries;
  }

  @NonNull
  private List<SearchQuery> buildSearchQueries()
  {
    final String normalizedStreet = getNormalizedStreet();
    final List<SearchQuery> queries = new ArrayList<>();
    if (ContactAddressNormalizer.looksLikeStructuredStreet(normalizedStreet))
    {
      final String context = getResolutionContext();
      final String separator = ContactAddressNormalizer.usesNorthAmericanFormatting(mFormattingCountry) ? " " : ", ";
      addQuery(queries, new SearchQuery(context.isEmpty() ? normalizedStreet : normalizedStreet + separator + context,
                                        normalizedStreet));

      final String withoutBareUnit = ContactAddressNormalizer.usesNorthAmericanFormatting(mFormattingCountry)
                                       ? ContactAddressNormalizer.possibleBareUnitStreet(normalizedStreet)
                                       : "";
      if (!withoutBareUnit.isEmpty())
      {
        addQuery(queries, new SearchQuery((withoutBareUnit + " " + context).trim(), withoutBareUnit));
      }
    }

    return queries;
  }

  @NonNull
  String getResolutionContext()
  {
    return mResolutionContext;
  }

  @NonNull
  private String normalizeResolutionContext()
  {
    if (!region.isEmpty() || !country.isEmpty())
      return ContactAddressNormalizer.normalizeContext(
          String.join(" ", locality, region, ContactAddressNormalizer.normalizeCountry(country)), mFormattingCountry);
    // Preserve disambiguating components even for formatted-only provider rows.
    final String preparedAddress = ContactAddressNormalizer.prepareAddress(address, mFormattingCountry);
    final String[] parts = preparedAddress.split(",", 2);
    if (parts.length == 2 && !parts[0].trim().matches("\\d+[A-Za-z]?"))
      return ContactAddressNormalizer.normalizeContext(parts[1], mFormattingCountry);
    final String normalized = ContactAddressNormalizer.normalizeContext(preparedAddress, mFormattingCountry);
    final String normalizedStreet = getNormalizedStreet();
    final List<String> tokens = ContactAddressNormalizer.matchTokens(normalized);
    final int streetTokens = ContactAddressNormalizer.matchTokens(normalizedStreet).size();
    return tokens.size() > streetTokens ? String.join(" ", tokens.subList(streetTokens, tokens.size())) : locality;
  }

  @NonNull
  String getAddressKey()
  {
    return mAddressKey;
  }

  private static void addQuery(@NonNull List<SearchQuery> queries, @NonNull SearchQuery candidate)
  {
    if (queries.stream().noneMatch(query -> query.query.equalsIgnoreCase(candidate.query)))
      queries.add(candidate);
  }
}
