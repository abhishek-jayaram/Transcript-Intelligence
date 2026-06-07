#!/usr/bin/env python3
"""Batch process all dataset folders through the classifier."""

import subprocess
from pathlib import Path

def process_dataset_folder(dataset_dir: Path, output_dir: Path, classifier_path: Path) -> bool:
    """Process a single dataset folder through the classifier.
    
    Returns True if successful, False otherwise.
    """
    folder_name = dataset_dir.name
    
    # Check if all required files exist
    required_files = [
        "meeting-info.json",
        "summary.json",
        "transcript.json",
        "speakers.json",
        "speaker-meta.json",
        "events.json",
    ]
    
    for file in required_files:
        if not (dataset_dir / file).exists():
            print(f"  ❌ {folder_name}: Missing {file}")
            return False
    
    try:
        # Build paths
        meeting_info_path = dataset_dir / "meeting-info.json"
        summary_path = dataset_dir / "summary.json"
        transcript_path = dataset_dir / "transcript.json"
        speakers_path = dataset_dir / "speakers.json"
        speaker_meta_path = dataset_dir / "speaker-meta.json"
        events_path = dataset_dir / "events.json"
        output_file = output_dir / f"cleaned_{folder_name}.json"
        
        # Run classifier via subprocess
        cmd = [
            "python",
            str(classifier_path),
            "--meeting-info", str(meeting_info_path),
            "--summary", str(summary_path),
            "--transcript", str(transcript_path),
            "--speakers", str(speakers_path),
            "--speaker-meta", str(speaker_meta_path),
            "--events", str(events_path),
            "--out", str(output_file),
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"  ❌ {folder_name}: {result.stderr[:100]}")
            return False
        
        print(f"  ✅ {folder_name}")
        return True
        
    except Exception as e:
        print(f"  ❌ {folder_name}: {str(e)[:100]}")
        return False


def main():
    workspace_dir = Path(__file__).parent
    dataset_dir = workspace_dir / "dataset"
    output_dir = workspace_dir / "cleaned_output"
    classifier_path = workspace_dir / "Data" / "classifier.py"
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Get all dataset folders
    folders = sorted([f for f in dataset_dir.iterdir() if f.is_dir()])
    
    print(f"Processing {len(folders)} dataset folders...\n")
    
    success_count = 0
    for i, folder in enumerate(folders, 1):
        print(f"[{i}/{len(folders)}]", end=" ")
        if process_dataset_folder(folder, output_dir, classifier_path):
            success_count += 1
    
    print(f"\n\n{'='*60}")
    print(f"✅ Completed: {success_count}/{len(folders)} folders processed successfully")
    print(f"📁 Output saved to: {output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
