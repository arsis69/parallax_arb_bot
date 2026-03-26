"""
Post-processing validation for AI-matched markets
Filters out false positives by validating:
1. FDV thresholds must match exactly (for same project)
2. Dates/months must match exactly
3. Project names must match exactly
4. Ordinals/qualifiers must match (most vs second most vs third most)
5. Number ranges must match (90-100 vs 110-120)
6. Competition/scope must match (Champions League vs Bundesliga)
7. Medal types must match (gold vs bronze)
"""

import json
import re
import sys
import io
from difflib import SequenceMatcher

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def extract_numbers(text):
    """Extract all monetary amounts, thresholds, and plain numbers"""
    numbers = set()

    # Pattern for RANGES FIRST: "$200-500b", "$100-200b"
    pattern_range = r'\$?(\d+)\s*[-\u2013\u2014]\s*(\d+)\s*(b|m|k|t|billion|million|thousand|trillion)\b'
    matches = re.finditer(pattern_range, text.lower())
    for match in matches:
        low, high, unit = match.groups()
        suffix = {'b': 'B', 'billion': 'B', 'm': 'M', 'million': 'M',
                  'k': 'K', 'thousand': 'K', 't': 'T', 'trillion': 'T'}.get(unit, unit.upper())
        numbers.add(f"{low}{suffix}")
        numbers.add(f"{high}{suffix}")

    # Pattern for "$500b+"
    pattern_plus = r'\$?(\d+)\s*(b|m|k|t)\s*\+'
    matches = re.finditer(pattern_plus, text.lower())
    for match in matches:
        amount, unit = match.groups()
        suffix = {'b': 'B', 'm': 'M', 'k': 'K', 't': 'T'}[unit]
        numbers.add(f"{amount}{suffix}+")

    # Dollar amounts with magnitude: "$600M", "$2B", "$1.5B"
    pattern1 = r'\$(\d+(?:\.\d+)?)\s*(b|m|k|t|billion|million|thousand|trillion)\b'
    matches = re.finditer(pattern1, text.lower())
    for match in matches:
        amount, unit = match.groups()
        suffix = {'b': 'B', 'billion': 'B', 'm': 'M', 'million': 'M',
                  'k': 'K', 'thousand': 'K', 't': 'T', 'trillion': 'T'}.get(unit, unit.upper())
        numbers.add(f"{amount}{suffix}")

    # Without dollar sign: "600M", "2B"
    pattern2 = r'\b(\d+(?:\.\d+)?)\s*(b|m|k|t|billion|million|thousand|trillion)\b'
    matches = re.finditer(pattern2, text.lower())
    for match in matches:
        amount, unit = match.groups()
        suffix = {'b': 'B', 'billion': 'B', 'm': 'M', 'million': 'M',
                  'k': 'K', 'thousand': 'K', 't': 'T', 'trillion': 'T'}.get(unit, unit.upper())
        numbers.add(f"{amount}{suffix}")

    # Stock prices and simple dollar amounts: "$150", "$200"
    pattern4 = r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\b'
    matches = re.finditer(pattern4, text)
    for match in matches:
        amount = match.group(1).replace(',', '')
        numbers.add(f"${amount}")

    # Plain number ranges: "between 90 and 100", "between 110 and 120"
    pattern_between = r'between\s+(\d+)\s+and\s+(\d+)'
    matches = re.finditer(pattern_between, text.lower())
    for match in matches:
        numbers.add(f"range_{match.group(1)}_{match.group(2)}")

    # "at least X" / "less than X" / "more than X"
    pattern_threshold = r'(?:at least|less than|more than|over|under|above|below)\s+(\d+(?:\.\d+)?)'
    matches = re.finditer(pattern_threshold, text.lower())
    for match in matches:
        numbers.add(f"threshold_{match.group(1)}")

    # Plain standalone numbers (catch things like '6 Fed rate cuts' vs '1 Fed rate cut')
    pattern_plain = r'\b(\d+(?:\.\d+)?)\b'
    matches = re.finditer(pattern_plain, text)
    for match in matches:
        num_str = match.group(1)
        # Skip 202x years to avoid false mismatches if one platform omits the year
        if num_str.startswith('202') and len(num_str) == 4:
            continue
        numbers.add(num_str)

    return numbers


def extract_months(text):
    """Extract standalone month references (no day required)"""
    months_found = set()
    month_names = [
        'january', 'february', 'march', 'april', 'may', 'june',
        'july', 'august', 'september', 'october', 'november', 'december'
    ]
    month_short = {
        'jan': 'january', 'feb': 'february', 'mar': 'march',
        'apr': 'april', 'jun': 'june', 'jul': 'july',
        'aug': 'august', 'sep': 'september', 'oct': 'october',
        'nov': 'november', 'dec': 'december'
    }

    text_lower = text.lower()

    for month in month_names:
        if month in text_lower:
            months_found.add(month)

    for short, full in month_short.items():
        # Match short form followed by space or period (avoid matching "march" from "marching")
        if re.search(r'\b' + short + r'[\s.]', text_lower):
            months_found.add(full)

    return months_found


def extract_dates(text):
    """Extract all dates - with or without year"""
    dates = set()
    month_day_pairs = set()

    month_map = {
        'jan': 'january', 'feb': 'february', 'mar': 'march',
        'apr': 'april', 'may': 'may', 'jun': 'june',
        'jul': 'july', 'aug': 'august', 'sep': 'september',
        'oct': 'october', 'nov': 'november', 'dec': 'december'
    }

    month_num_to_name = {
        '01': 'january', '02': 'february', '03': 'march', '04': 'april',
        '05': 'may', '06': 'june', '07': 'july', '08': 'august',
        '09': 'september', '10': 'october', '11': 'november', '12': 'december'
    }

    # ISO date format: "2026-02-17", "2026-02-21"
    pattern_iso = r'(\d{4})-(\d{2})-(\d{2})'
    matches = re.finditer(pattern_iso, text)
    for match in matches:
        year, month_num, day = match.groups()
        month_name = month_num_to_name.get(month_num)
        if month_name:
            # Remove leading zeros from day
            day_clean = str(int(day))
            month_day_pairs.add(f"{month_name}_{day_clean}")
            dates.add(f"{month_name}_{day_clean}_{year}")

    # Full date: "January 31, 2026", "January 31st, 2026"
    pattern1 = r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})?'
    matches = re.finditer(pattern1, text.lower())
    for match in matches:
        month, day, year = match.groups()
        month_day_pairs.add(f"{month}_{day}")
        if year:
            dates.add(f"{month}_{day}_{year}")

    # Short form: "Jan 31", "Jun 30, 2026"
    pattern2 = r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})?'
    matches = re.finditer(pattern2, text.lower())
    for match in matches:
        month, day, year = match.groups()
        full_month = month_map.get(month[:3], month)
        month_day_pairs.add(f"{full_month}_{day}")
        if year:
            dates.add(f"{full_month}_{day}_{year}")

    # "by June 30" without year
    pattern3 = r'by\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?'
    matches = re.finditer(pattern3, text.lower())
    for match in matches:
        month, day = match.groups()
        month_day_pairs.add(f"{month}_{day}")

    return dates, month_day_pairs


def extract_ordinals(text):
    """Extract ranking/ordinal qualifiers that completely change market meaning"""
    qualifiers = set()
    text_lower = text.lower()

    # Gender qualifiers - CRITICAL for sports markets
    if re.search(r"\bmen'?s\b", text_lower) or re.search(r'\bmens\b', text_lower):
        qualifiers.add('gender_mens')
    if re.search(r"\bwomen'?s\b", text_lower) or re.search(r'\bwomens\b', text_lower):
        qualifiers.add('gender_womens')

    # Ordinal rankings: "second most", "third most", "most"
    if re.search(r'\bthird[\s-]+most\b', text_lower):
        qualifiers.add('third_most')
    elif re.search(r'\bsecond[\s-]+most\b', text_lower):
        qualifiers.add('second_most')
    elif re.search(r'\bmost\b', text_lower):
        qualifiers.add('most')

    # Largest/biggest rankings
    if re.search(r'\bthird[\s-]+largest\b', text_lower):
        qualifiers.add('third_largest')
    elif re.search(r'\bsecond[\s-]+largest\b', text_lower):
        qualifiers.add('second_largest')
    elif re.search(r'\blargest\b', text_lower):
        qualifiers.add('largest')

    # "record a medal" vs "win the most medals"
    if re.search(r'\brecord\s+a\s+medal\b', text_lower):
        qualifiers.add('record_a_medal')
    if re.search(r'\brecord\s+a\s+gold\b', text_lower):
        qualifiers.add('record_a_gold')

    # Medal types
    if 'gold medal' in text_lower or 'gold medals' in text_lower:
        qualifiers.add('medal_gold')
    if 'silver medal' in text_lower or 'silver medals' in text_lower:
        qualifiers.add('medal_silver')
    if 'bronze medal' in text_lower or 'bronze medals' in text_lower:
        qualifiers.add('medal_bronze')

    # "played first" vs "played at" vs "played last"
    if re.search(r'\bplayed\s+first\b', text_lower) or re.search(r'\bbe\s+played\s+first\b', text_lower):
        qualifiers.add('played_first')
    elif re.search(r'\bplayed\s+last\b', text_lower) or re.search(r'\bbe\s+played\s+last\b', text_lower):
        qualifiers.add('played_last')
    elif re.search(r'\bplayed\s+at\b', text_lower) or re.search(r'\bbe\s+played\b(?!\s+(?:first|last))', text_lower):
        qualifiers.add('played_at')

    # "win Group X" vs "win (tournament)" — scope difference
    group_match = re.search(r'\bwin\s+group\s+([a-z])\b', text_lower)
    if group_match:
        qualifiers.add(f'win_group_{group_match.group(1)}')
    elif re.search(r'\bwin\s+the\b.*\b(world cup|cup|championship|league)\b', text_lower):
        qualifiers.add('win_tournament')
    elif re.search(r'\bwin\b', text_lower) and not group_match:
        qualifiers.add('win_overall')

    return qualifiers


def extract_competition(text):
    """Extract specific competition/league names"""
    competitions = set()
    text_lower = text.lower()

    comp_names = [
        'champions league', 'bundesliga', 'premier league', 'la liga',
        'serie a', 'ligue 1', 'europa league', 'conference league',
        'world cup', 'euros', 'copa america', 'nations league'
    ]

    for comp in comp_names:
        if comp in text_lower:
            competitions.add(comp)

    return competitions


def extract_project_name(text):
    """Extract project/entity name for FDV markets"""
    text_lower = text.lower()

    projects = [
        'megaeth', 'metamask', 'opensea', 'infinex', 'gensyn',
        'base', 'based', 'edgex', 'abstract', 'polymarket', 'nansen',
        'pacifica', 'blackpink', 'newjeans', 'babymonster',
        'alex honnold', 'zelenskyy', 'khamenei', 'trump',
        'tim cook', 'netflix', 'warner bros', 'paramount'
    ]

    for project in projects:
        if project in text_lower:
            return project

    # Extract capitalized words (likely project names)
    pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    matches = re.findall(pattern, text)
    if matches:
        return matches[0].lower()

    return None


def extract_party_combo(text):
    """Extract political party combinations like 'D Senate, R House'"""
    text_upper = text.upper()
    combo = set()

    # Match patterns like "D Senate", "R House", "R Senate", "D House"
    senate_match = re.search(r'([DR])\s*SENATE', text_upper)
    house_match = re.search(r'([DR])\s*HOUSE', text_upper)

    if senate_match:
        combo.add(f"senate_{senate_match.group(1)}")
    if house_match:
        combo.add(f"house_{house_match.group(1)}")

    return combo


def extract_event_context(market):
    """Extract event context from market metadata (slugs, URLs) to detect different events"""
    context = set()

    # Get slugs/URLs
    slug = market.get('slug', '')
    event_slug = market.get('event_slug', '')
    category_slug = market.get('category_slug', '')
    url = market.get('url', '')

    # Combine all identifiers
    all_identifiers = f"{slug} {event_slug} {category_slug} {url}".lower()

    # Extract league/competition codes
    league_codes = re.findall(r'\b(ucl|epl|lal|sea|bun|fl1|por|cdr|mwoh)\b', all_identifiers)
    for code in league_codes:
        context.add(f'league_{code}')

    # Extract opponent codes (3-letter team codes)
    # Pattern: team codes in slugs like "ucl-ben-rma" (Benfica vs Real Madrid)
    team_codes = re.findall(r'\b([a-z]{3})-([a-z]{3,4})-\d{4}-\d{2}-\d{2}\b', all_identifiers)
    for match in team_codes:
        # Sort teams to catch both "ben-rma" and "rma-ben" as same matchup
        teams = tuple(sorted(match))
        context.add(f'matchup_{"_".join(teams)}')

    # Extract date from slug: YYYY-MM-DD
    slug_date_match = re.search(r'\b(20\d{2}-\d{2}-\d{2})\b', all_identifiers)
    if slug_date_match:
        context.add(f'slug_date_{slug_date_match.group(1)}')

    return context


def validate_match(market_a, market_b, similarity):
    """
    Validate if two AI-matched markets are truly the same
    Returns (is_valid, reason)
    """
    title_a = market_a['title']
    title_b = market_b['title']

    # Extract context from both titles
    numbers_a = extract_numbers(title_a)
    numbers_b = extract_numbers(title_b)
    dates_a, month_day_a = extract_dates(title_a)
    dates_b, month_day_b = extract_dates(title_b)
    months_a = extract_months(title_a)
    months_b = extract_months(title_b)
    ordinals_a = extract_ordinals(title_a)
    ordinals_b = extract_ordinals(title_b)
    comps_a = extract_competition(title_a)
    comps_b = extract_competition(title_b)
    project_a = extract_project_name(title_a)
    project_b = extract_project_name(title_b)
    party_a = extract_party_combo(title_a)
    party_b = extract_party_combo(title_b)

    # Extract event context from market metadata (URLs, slugs)
    event_ctx_a = extract_event_context(market_a)
    event_ctx_b = extract_event_context(market_b)

    # Rule 0: Event context MUST match if detected (prevents different games of same team)
    # Only check if BOTH have event identifiers (we now check slug_date instead of full event_slug)
    slug_dates_a = {x for x in event_ctx_a if x.startswith('slug_date_')}
    slug_dates_b = {x for x in event_ctx_b if x.startswith('slug_date_')}
    if slug_dates_a and slug_dates_b:
        if not slug_dates_a.intersection(slug_dates_b):
            return False, f"Different events (slug dates): {slug_dates_a} vs {slug_dates_b}"

    # Rule 1: Numbers MUST match if both have them
    if numbers_a and numbers_b:
        if numbers_a != numbers_b:
            return False, f"Different numbers: {numbers_a} vs {numbers_b}"

    # Rule 2: Specific dates (month+day) must match
    if month_day_a and month_day_b:
        if not month_day_a.intersection(month_day_b):
            return False, f"Different dates: {month_day_a} vs {month_day_b}"

    if dates_a and dates_b:
        if not dates_a.intersection(dates_b):
            return False, f"Different full dates: {dates_a} vs {dates_b}"

    # Rule 3: Months must match if both have them (catches "February" vs "June")
    if months_a and months_b:
        if not months_a.intersection(months_b):
            return False, f"Different months: {months_a} vs {months_b}"

    # Rule 4: Ordinal/qualifier mismatch = different market entirely
    if ordinals_a and ordinals_b:
        if ordinals_a != ordinals_b:
            return False, f"Different qualifiers: {ordinals_a} vs {ordinals_b}"
    elif ordinals_a or ordinals_b:
        # One has qualifiers, other doesn't — likely different
        diff = ordinals_a.symmetric_difference(ordinals_b)
        # Only reject if the qualifier is meaningful (ranking words)
        ranking_words = {'most', 'second_most', 'third_most', 'largest', 'second_largest',
                         'third_largest', 'record_a_medal', 'record_a_gold',
                         'played_first', 'played_last', 'played_at',
                         'medal_gold', 'medal_silver', 'medal_bronze',
                         'win_tournament', 'gender_mens', 'gender_womens'}
        meaningful_diff = diff.intersection(ranking_words)
        # Also check win_group_* patterns
        for d in diff:
            if d.startswith('win_group_'):
                meaningful_diff.add(d)
        if meaningful_diff:
            return False, f"Qualifier mismatch: {ordinals_a} vs {ordinals_b}"

    # Rule 5: Competition must match if both detected
    if comps_a and comps_b:
        if not comps_a.intersection(comps_b):
            return False, f"Different competitions: {comps_a} vs {comps_b}"

    # Rule 6: Political party combo must match
    if party_a and party_b:
        if party_a != party_b:
            return False, f"Different party combos: {party_a} vs {party_b}"

    # Rule 7: Project names should match if both detected
    if project_a and project_b:
        if project_a != project_b:
            if SequenceMatcher(None, project_a, project_b).ratio() < 0.85:
                return False, f"Different projects: {project_a} vs {project_b}"

    # Passed all checks
    return True, "Valid"


def main():
    print("Loading AI-matched markets...")
    with open('similar_options_embeddings.json', 'r', encoding='utf-8') as f:
        matches = json.load(f)

    print(f"Total AI matches: {len(matches)}")

    validated_matches = []
    rejected_matches = []

    print("\nValidating matches...")
    for idx, match in enumerate(matches, 1):
        similarity = match['similarity']
        markets = match['markets']

        if len(markets) < 2:
            continue

        market_a = markets[0]
        market_b = markets[1]

        # Validate
        is_valid, reason = validate_match(market_a, market_b, similarity)

        if is_valid:
            # Attach validation context to the match
            match['validation'] = {
                'status': 'valid',
                'reason': reason,
                'context_a': {
                    'numbers': list(extract_numbers(market_a['title'])),
                    'months': list(extract_months(market_a['title'])),
                    'ordinals': list(extract_ordinals(market_a['title']))
                },
                'context_b': {
                    'numbers': list(extract_numbers(market_b['title'])),
                    'months': list(extract_months(market_b['title'])),
                    'ordinals': list(extract_ordinals(market_b['title']))
                }
            }
            validated_matches.append(match)
        else:
            rejected_matches.append({
                'match': match,
                'reason': reason,
                'similarity': similarity
            })

            if similarity >= 0.95:  # Log high-similarity rejections
                print(f"\n  REJECTED (sim={similarity:.3f}): {reason}")
                print(f"    A: {market_a['title'][:80]}")
                print(f"    B: {market_b['title'][:80]}")

    print(f"\n{'='*100}")
    print(f"VALIDATION COMPLETE")
    print(f"{'='*100}")
    print(f"Total AI matches: {len(matches)}")
    print(f"Validated matches: {len(validated_matches)}")
    print(f"Rejected matches: {len(rejected_matches)}")
    if len(matches) > 0:
        print(f"Validation rate: {len(validated_matches)/len(matches)*100:.1f}%")
    else:
        print(f"Validation rate: N/A (no matches to validate)")
    print(f"{'='*100}\n")

    # Save validated matches
    with open('similar_options_validated_ai.json', 'w', encoding='utf-8') as f:
        json.dump(validated_matches, f, indent=2)

    # Save rejection report
    with open('rejected_matches_report.json', 'w', encoding='utf-8') as f:
        json.dump(rejected_matches, f, indent=2)

    print(f"Validated matches saved to: similar_options_validated_ai.json")
    print(f"Rejection report saved to: rejected_matches_report.json")

    # Show distribution
    print(f"\n{'='*100}")
    print("VALIDATED MATCHES BY SIMILARITY")
    print(f"{'='*100}")

    ranges = [
        (0.99, 1.00, "99-100% (perfect)"),
        (0.95, 0.99, "95-99% (very high)"),
        (0.90, 0.95, "90-95% (high)")
    ]

    for min_sim, max_sim, label in ranges:
        count = len([m for m in validated_matches if min_sim <= m['similarity'] < max_sim])
        print(f"  {label}: {count} matches")

    # Show rejection reasons
    print(f"\n{'='*100}")
    print("TOP REJECTION REASONS")
    print(f"{'='*100}")

    reasons = {}
    for rej in rejected_matches:
        reason_key = rej['reason'].split(':')[0]
        if reason_key not in reasons:
            reasons[reason_key] = 0
        reasons[reason_key] += 1

    for reason, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
        print(f"  {reason}: {count} matches")

    print(f"\n{'='*100}\n")

    # Show top 20 validated matches
    print(f"{'='*100}")
    print("TOP 20 VALIDATED MATCHES")
    print(f"{'='*100}\n")

    for idx, match in enumerate(validated_matches[:20], 1):
        sim = match['similarity']
        markets = match['markets']

        print(f"\n{idx}. Similarity: {sim:.4f} ({sim*100:.2f}%)")
        for m in markets:
            title_clean = m['title'][:80].encode('ascii', 'ignore').decode('ascii')
            print(f"   [{m['platform'].upper()}] {title_clean}")


if __name__ == "__main__":
    main()
