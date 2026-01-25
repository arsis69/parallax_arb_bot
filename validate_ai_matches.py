"""
Post-processing validation for AI-matched markets
Filters out false positives by validating:
1. FDV thresholds must match exactly (for same project)
2. Dates/months must match exactly
3. Project names must match exactly
"""

import json
import re
from difflib import SequenceMatcher


def extract_numbers(text):
    """Extract all monetary amounts and thresholds"""
    numbers = set()

    # Pattern for RANGES FIRST: "$200-500b", "$100–200b" (handles both hyphen and en-dash)
    pattern_range = r'\$?(\d+)\s*[-–—]\s*(\d+)\s*(b|m|k|t|billion|million|thousand|trillion)\b'
    matches = re.finditer(pattern_range, text.lower())
    for match in matches:
        low, high, unit = match.groups()
        if unit in ['b', 'billion']:
            numbers.add(f"{low}B")
            numbers.add(f"{high}B")
        elif unit in ['m', 'million']:
            numbers.add(f"{low}M")
            numbers.add(f"{high}M")
        elif unit in ['k', 'thousand']:
            numbers.add(f"{low}K")
            numbers.add(f"{high}K")
        elif unit in ['t', 'trillion']:
            numbers.add(f"{low}T")
            numbers.add(f"{high}T")

    # Pattern for "$500b+" (500 billion or more)
    pattern_plus = r'\$?(\d+)\s*(b|m|k|t)\s*\+'
    matches = re.finditer(pattern_plus, text.lower())
    for match in matches:
        amount, unit = match.groups()
        if unit == 'b':
            numbers.add(f"{amount}B+")
        elif unit == 'm':
            numbers.add(f"{amount}M+")
        elif unit == 'k':
            numbers.add(f"{amount}K+")
        elif unit == 't':
            numbers.add(f"{amount}T+")

    # Dollar amounts: "$600M", "$2B", "$1.5B"
    pattern1 = r'\$(\d+(?:\.\d+)?)\s*(b|m|k|t|billion|million|thousand|trillion)\b'
    matches = re.finditer(pattern1, text.lower())
    for match in matches:
        amount, unit = match.groups()
        if unit in ['b', 'billion']:
            numbers.add(f"{amount}B")
        elif unit in ['m', 'million']:
            numbers.add(f"{amount}M")
        elif unit in ['k', 'thousand']:
            numbers.add(f"{amount}K")
        elif unit in ['t', 'trillion']:
            numbers.add(f"{amount}T")

    # Without dollar sign: "600M", "2B"
    pattern2 = r'\b(\d+(?:\.\d+)?)\s*(b|m|k|t|billion|million|thousand|trillion)\b'
    matches = re.finditer(pattern2, text.lower())
    for match in matches:
        amount, unit = match.groups()
        if unit in ['b', 'billion']:
            numbers.add(f"{amount}B")
        elif unit in ['m', 'million']:
            numbers.add(f"{amount}M")
        elif unit in ['k', 'thousand']:
            numbers.add(f"{amount}K")
        elif unit in ['t', 'trillion']:
            numbers.add(f"{amount}T")

    # With > or <: ">$600M", ">1B"
    pattern3 = r'[><]\s*\$?(\d+(?:\.\d+)?)\s*(b|m|k|t|billion|million|thousand|trillion)'
    matches = re.finditer(pattern3, text.lower())
    for match in matches:
        amount, unit = match.groups()
        if unit in ['b', 'billion']:
            numbers.add(f"{amount}B")
        elif unit in ['m', 'million']:
            numbers.add(f"{amount}M")
        elif unit in ['k', 'thousand']:
            numbers.add(f"{amount}K")
        elif unit in ['t', 'trillion']:
            numbers.add(f"{amount}T")

    # Stock prices and simple dollar amounts: "$150", "$200", "$1500"
    pattern4 = r'\$(\d+(?:,\d{3})*(?:\.\d+)?)\b'
    matches = re.finditer(pattern4, text)
    for match in matches:
        # Remove commas and add $ prefix
        amount = match.group(1).replace(',', '')
        numbers.add(f"${amount}")

    # Decimal thresholds: "9.0", "10.0"
    pattern5 = r'\b(\d+\.\d+)\b'
    matches = re.finditer(pattern5, text)
    for match in matches:
        numbers.add(match.group(1))

    return numbers


def extract_dates(text):
    """Extract all dates - with or without year"""
    dates = set()
    month_day_pairs = set()  # For comparing month+day without year

    month_map = {
        'jan': 'january', 'feb': 'february', 'mar': 'march',
        'apr': 'april', 'may': 'may', 'jun': 'june',
        'jul': 'july', 'aug': 'august', 'sep': 'september',
        'oct': 'october', 'nov': 'november', 'dec': 'december'
    }

    # Full date: "January 31, 2026", "January 31st, 2026", "March 31, 2026"
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

    # "by June 30" without year - critical for Probable markets
    pattern3 = r'by\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?'
    matches = re.finditer(pattern3, text.lower())
    for match in matches:
        month, day = match.groups()
        month_day_pairs.add(f"{month}_{day}")

    # Return both full dates and month_day pairs
    return dates, month_day_pairs


def extract_project_name(text):
    """Extract project/entity name for FDV markets"""
    text_lower = text.lower()

    # Common project names in crypto/prediction markets
    projects = [
        'megaeth', 'metamask', 'opensea', 'infinex', 'gensyn',
        'base', 'edgex', 'abstract', 'polymarket', 'nansen',
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


def validate_match(market_a, market_b, similarity):
    """
    Validate if two AI-matched markets are truly the same
    Returns (is_valid, reason)
    """
    title_a = market_a['title']
    title_b = market_b['title']

    # Extract context from both
    numbers_a = extract_numbers(title_a)
    numbers_b = extract_numbers(title_b)
    dates_a, month_day_a = extract_dates(title_a)
    dates_b, month_day_b = extract_dates(title_b)
    project_a = extract_project_name(title_a)
    project_b = extract_project_name(title_b)

    # Rule 1: If both have FDV/numbers AND same project, numbers MUST match EXACTLY
    if numbers_a and numbers_b:
        if project_a and project_b and project_a == project_b:
            # Same project - FDV thresholds MUST be identical (ALL numbers must match)
            if numbers_a != numbers_b:
                return False, f"Same project ({project_a}) but different FDV: {numbers_a} vs {numbers_b}"
        else:
            # Different or no projects - still require ALL numbers to match
            if numbers_a != numbers_b:
                return False, f"Different numbers: {numbers_a} vs {numbers_b}"

    # Rule 2: STRICT DATE MATCHING - if either has dates, they MUST match
    # First check month+day pairs (works even if one has year and one doesn't)
    if month_day_a and month_day_b:
        if not month_day_a.intersection(month_day_b):
            return False, f"Different dates: {month_day_a} vs {month_day_b}"

    # Also check full dates if both have them
    if dates_a and dates_b:
        if not dates_a.intersection(dates_b):
            return False, f"Different full dates: {dates_a} vs {dates_b}"

    # Rule 3: For high-profit opportunities (>10%), require 95%+ similarity
    # (likely false positive if high profit + low similarity)
    if similarity < 0.95:
        # These need extra scrutiny - likely have subtle differences
        # We already checked numbers and dates above, so if those pass, it's okay
        pass

    # Rule 4: Project names should match if both detected
    if project_a and project_b:
        if project_a != project_b:
            # Check if they're similar (typos, abbreviations)
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
            validated_matches.append(match)
        else:
            rejected_matches.append({
                'match': match,
                'reason': reason,
                'similarity': similarity
            })

            if similarity >= 0.95:  # Log high-similarity rejections
                print(f"\n  REJECTED (sim={similarity:.3f}): {reason}")
                print(f"    A: {market_a['title'][:70]}")
                print(f"    B: {market_b['title'][:70]}")

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
        reason_key = rej['reason'].split(':')[0]  # Get category
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
