from local_notebooklm.processor import podcast_processor

success, result = podcast_processor(
    input_path="./examples/MoshiVis.pdf",
    config_path="config.json",
    format_type="summary",
    length="short",
    style="academic",
    # preference="Focus on the key technical aspects, this podcast should only be for Machine Learning researchers and engineers.",
    output_dir="./web_ui/output",
    skip_to=4
)

if success:
        print(f"✅ Podcast generated at: {result}")
else:
    print(f"❌ Failed: {result}")