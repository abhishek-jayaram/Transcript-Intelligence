"""Combine all cleaned meeting data into a single master file."""

import json
from pathlib import Path
from typing import List, Dict, Any

def combine_cleaned_data(cleaned_output_dir: Path, output_file: Path) -> None:
    """Combine all cleaned JSON files into a single master file.
    
    The master file will have structure:
    {
        "metadata": {
            "total_meetings": int,
            "generated_at": str,
            "source_directory": str
        },
        "meetings": [
            {...cleaned meeting 1...},
            {...cleaned meeting 2...},
            ...
        ]
    }
    """
    # Get all cleaned JSON files
    json_files = sorted(cleaned_output_dir.glob("cleaned_*.json"))
    
    print(f"Found {len(json_files)} cleaned meeting files")
    print("Combining into master file...\n")
    
    meetings = []
    
    for i, file in enumerate(json_files, 1):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                meetings.append(data)
            print(f"[{i}/{len(json_files)}] ✅ {file.name}")
        except Exception as e:
            print(f"[{i}/{len(json_files)}] ❌ {file.name}: {str(e)[:80]}")
    
    # Create master structure
    master_data = {
        "metadata": {
            "total_meetings": len(meetings),
            "generated_at": "2026-06-06",
            "source_directory": str(cleaned_output_dir),
        },
        "meetings": meetings
    }
    
    # Save master file
    print(f"\nWriting master file to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Master file created successfully!")
    print(f"📊 Statistics:")
    print(f"   - Total meetings: {len(meetings)}")
    print(f"   - File size: {output_file.stat().st_size / (1024*1024):.2f} MB")
    print(f"   - Location: {output_file}")


def main():
    workspace_dir = Path(__file__).parent
    cleaned_output_dir = workspace_dir / "cleaned_output"
    master_file = workspace_dir / "master_meetings.json"
    
    if not cleaned_output_dir.exists():
        print(f"❌ Cleaned output directory not found: {cleaned_output_dir}")
        return
    
    combine_cleaned_data(cleaned_output_dir, master_file)


if __name__ == "__main__":
    main()
