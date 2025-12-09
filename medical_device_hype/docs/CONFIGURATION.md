# Surgical Device Filtering Configuration

## Overview

The surgical device filtering system uses a JSON configuration file to define keywords and filtering rules. This allows you to easily adjust the filtering criteria without modifying the code.

## Configuration File Location

Default location: `data/surgical_device_filter_config.json`

You can also specify a custom config file when initializing the analyzer:

```python
from src.surgery_device_analysis import SurgeryDeviceAnalyzer

analyzer = SurgeryDeviceAnalyzer(
    config_file="path/to/custom_config.json"
)
```

## Configuration Structure

The configuration file contains the following sections:

### 1. `surgical_specialties`

Defines keywords for each surgical specialty. Devices matching these keywords will be categorized accordingly.

```json
{
  "surgical_specialties": {
    "cardiac_surgery": ["cardiac", "heart", "cardiovascular", ...],
    "orthopedic_surgery": ["orthopedic", "joint", "knee", ...],
    ...
  }
}
```

**To add a new specialty:**
1. Add a new key to `surgical_specialties`
2. Add an array of keywords that identify devices in that specialty

**To modify keywords:**
1. Edit the keyword arrays for existing specialties
2. Add or remove keywords as needed

### 2. `specific_surgical_terms`

General surgical terms that indicate a device is surgical (beyond specialty-specific terms).

```json
{
  "specific_surgical_terms": [
    "surgery",
    "surgical",
    "surgical robot",
    "laparoscopic",
    ...
  ]
}
```

**To modify:**
- Add terms to include more devices
- Remove terms to be more restrictive

### 3. `exclusion_patterns`

Keywords that indicate a device is **NOT** surgical. Devices matching these patterns are excluded.

```json
{
  "exclusion_patterns": [
    "diagnostic",
    "test",
    "imaging",
    "software",
    ...
  ]
}
```

**To modify:**
- Add patterns to exclude more non-surgical devices
- Remove patterns if you want to be less restrictive

### 4. `exclusion_exceptions`

Exception patterns for exclusion rules. If a device contains "surgical" AND matches one of these exclusion patterns, it may still be considered surgical.

```json
{
  "exclusion_exceptions": [
    "diagnostic",
    "monitor"
  ]
}
```

**Example:** A "surgical diagnostic monitor" would be allowed because it contains "surgical" and "diagnostic" is in the exceptions list.

### 5. `surgical_robot_brands`

Specific terms for surgical robot systems that should be considered surgical.

```json
{
  "surgical_robot_brands": [
    "surgical robot",
    "robotic surgery",
    "da vinci",
    "mako",
    "rosa"
  ]
}
```

**To add new robot brands:**
- Add the brand name or model to this list

### 6. `filtering_settings`

Configuration options for filtering behavior.

```json
{
  "filtering_settings": {
    "require_specific_surgical_term": true,
    "case_sensitive": false,
    "match_whole_words_only": false
  }
}
```

**Options:**
- `require_specific_surgical_term`: If `true`, devices must match at least one specialty-specific keyword (not just generic "surgery" terms). Set to `false` to be more permissive.
- `case_sensitive`: Currently not implemented, reserved for future use
- `match_whole_words_only`: Currently not implemented, reserved for future use

## How to Modify the Configuration

### Method 1: Edit the JSON file directly

1. Open `data/surgical_device_filter_config.json`
2. Edit the keywords as needed
3. Save the file
4. Restart your analysis

### Method 2: Create a custom config file

1. Copy `data/surgical_device_filter_config.json` to a new location
2. Modify the copy
3. Specify the custom file when initializing:

```python
analyzer = SurgeryDeviceAnalyzer(
    config_file="my_custom_config.json"
)
```

## Examples

### Adding a New Surgical Specialty

```json
{
  "surgical_specialties": {
    "cardiac_surgery": [...],
    "new_specialty": [
      "keyword1",
      "keyword2",
      "keyword3"
    ]
  }
}
```

### Making Filtering More Restrictive

1. Add more terms to `exclusion_patterns`
2. Set `require_specific_surgical_term` to `true`
3. Remove generic terms from `specific_surgical_terms`

### Making Filtering More Permissive

1. Remove terms from `exclusion_patterns`
2. Set `require_specific_surgical_term` to `false`
3. Add more generic terms to `specific_surgical_terms`

## Validation

The system will:
- Load the config file on initialization
- Fall back to default configuration if the file is missing or invalid
- Display a message indicating which config was loaded (if verbose mode is enabled)

## Best Practices

1. **Backup your config** before making changes
2. **Test changes** on a small dataset first
3. **Document custom keywords** you add
4. **Keep keywords lowercase** (matching is case-insensitive)
5. **Use specific terms** rather than generic ones for better accuracy

## Troubleshooting

**Config file not found:**
- Check that the file exists at `data/surgical_device_filter_config.json`
- The system will use default configuration if file is missing

**Changes not taking effect:**
- Make sure you're editing the correct config file
- Restart your Python session/script after making changes
- Check that the config file is valid JSON (use a JSON validator)

**Too many/few devices being filtered:**
- Adjust `exclusion_patterns` to exclude more/fewer devices
- Modify `require_specific_surgical_term` setting
- Review and adjust specialty keywords

