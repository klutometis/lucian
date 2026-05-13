#!/usr/bin/env bash
# Batch annotate + render across all dialogues for a given translation model.
# Skip-if-exists at each stage (annotation, render). Resumable.
#
# Usage:
#   pipeline/run_all.sh anthropic/claude-opus-4-7 hume
#   pipeline/run_all.sh openai/gpt-5.5 elevenlabs
set -euo pipefail

translation_model="${1:-anthropic/claude-opus-4-7}"
provider="${2:-hume}"
work="${3:-lucian-dialogues-of-the-dead}"

safe_tm="${translation_model//\//-}"
safe_tm="${safe_tm//:/-}"

work_dir="works/$work"
tr_dir="$work_dir/output/translations"
ann_dir="$work_dir/output/annotations"
audio_dir="$work_dir/output/audio"

dialogues=$(ls "$tr_dir" | grep "_${safe_tm}.json$" | sed 's/dialogue_\([0-9]*\)_.*/\1/' | sort -u)

for d in $dialogues; do
  echo "=== dialogue $d ==="
  ann_path="$ann_dir/dialogue_${d}_${safe_tm}_annotated.json"
  audio_path="$audio_dir/dialogue_${d}_${safe_tm}_${provider}.wav"

  if [ ! -f "$ann_path" ]; then
    uv run pipeline/tts/driver.py --dialogue "${d#0}" --translation-model "$translation_model" --annotation-model openai/gpt-5.5 \
      2>&1 | grep -E "INFO Saved|ERROR" | tail -2 || true
  else
    echo "  annotation cached"
  fi

  if [ ! -f "$audio_path" ]; then
    uv run pipeline/tts/render.py --dialogue "${d#0}" --translation-model "$translation_model" --provider "$provider" \
      2>&1 | grep -E "INFO Saved|ERROR|WARNING" | tail -3 || true
  else
    echo "  audio cached"
  fi
done

echo
echo "Done. Audio in: $audio_dir/"
ls -lh "$audio_dir"/*"${safe_tm}_${provider}.wav" 2>/dev/null | wc -l
echo "files."
