#!/usr/bin/env python3
"""
Validate specification files for completeness and consistency.
Part of the spec-driven development workflow.
"""

import os
import yaml
import sys
from pathlib import Path
import re

def validate_spec_structure(spec_path):
    """Validate that a specification has the required structure."""
    required_sections = [
        "# Specification:",
        "## Overview",
        "## Problem Statement",
        "## User Stories",
        "## Functional Requirements",
        "## Success Metrics",
        "## Implementation"
    ]

    with open(spec_path, 'r', encoding='utf-8') as f:
        content = f.read()

    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)

    return missing_sections

def validate_yaml_blocks(spec_path):
    """Validate YAML code blocks in specifications."""
    with open(spec_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find YAML code blocks
    yaml_pattern = r'```yaml\n(.*?)\n```'
    yaml_blocks = re.findall(yaml_pattern, content, re.DOTALL)

    errors = []
    for i, yaml_block in enumerate(yaml_blocks):
        try:
            yaml.safe_load(yaml_block)
        except yaml.YAMLError as e:
            errors.append(f"YAML block {i+1}: {str(e)}")

    return errors

def validate_user_stories(spec_path):
    """Validate that user stories follow the correct format."""
    with open(spec_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Look for user stories section
    user_stories_pattern = r'## User Stories\n(.*?)(?=\n##|\Z)'
    match = re.search(user_stories_pattern, content, re.DOTALL)

    if not match:
        return ["No User Stories section found"]

    user_stories_content = match.group(1)

    # Check for proper user story format
    story_pattern = r'### As a .+\n(?:- I want .+\n)+'
    stories = re.findall(story_pattern, user_stories_content, re.MULTILINE)

    if not stories:
        return ["No properly formatted user stories found (should be: '### As a [role]' followed by '- I want [goal]')"]

    return []

def validate_success_metrics(spec_path):
    """Validate that success metrics are quantifiable."""
    with open(spec_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Look for success metrics section
    metrics_pattern = r'## Success Metrics\n(.*?)(?=\n##|\Z)'
    match = re.search(metrics_pattern, content, re.DOTALL)

    if not match:
        return ["No Success Metrics section found"]

    metrics_content = match.group(1)

    # Check for quantifiable metrics (should contain numbers, percentages, or time units)
    quantifiable_pattern = r'[0-9]+[%]?|<[0-9]+|>[0-9]+|[0-9]+(?:ms|s|min|hours?|days?|weeks?|months?)'

    if not re.search(quantifiable_pattern, metrics_content):
        return ["Success metrics should include quantifiable targets (numbers, percentages, time units)"]

    return []

def main():
    """Main validation function."""
    specs_dir = Path("specs")

    if not specs_dir.exists():
        print("❌ No specs directory found")
        sys.exit(1)

    all_valid = True

    # Find all spec files
    spec_files = list(specs_dir.glob("*/spec.md"))

    if not spec_files:
        print("❌ No specification files found in specs/ directories")
        sys.exit(1)

    print(f"🔍 Validating {len(spec_files)} specification files...")

    for spec_file in spec_files:
        print(f"\n📋 Validating {spec_file}")

        # Structure validation
        missing_sections = validate_spec_structure(spec_file)
        if missing_sections:
            print(f"❌ Missing required sections: {', '.join(missing_sections)}")
            all_valid = False

        # YAML validation
        yaml_errors = validate_yaml_blocks(spec_file)
        if yaml_errors:
            print(f"❌ YAML errors: {'; '.join(yaml_errors)}")
            all_valid = False

        # User stories validation
        story_errors = validate_user_stories(spec_file)
        if story_errors:
            print(f"❌ User story errors: {'; '.join(story_errors)}")
            all_valid = False

        # Success metrics validation
        metrics_errors = validate_success_metrics(spec_file)
        if metrics_errors:
            print(f"❌ Success metrics errors: {'; '.join(metrics_errors)}")
            all_valid = False

        if not (missing_sections or yaml_errors or story_errors or metrics_errors):
            print("✅ Specification is valid")

    # Summary
    print(f"\n{'='*50}")
    if all_valid:
        print("✅ All specifications are valid!")
        sys.exit(0)
    else:
        print("❌ Some specifications have validation errors")
        sys.exit(1)

if __name__ == "__main__":
    main()