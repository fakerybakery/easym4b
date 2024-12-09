import click
import ffmpeg
import os
from tqdm import tqdm
import concurrent.futures
import re
from slugify import slugify
import math
import json

def get_file_info(input_file):
    """Extract chapter information, global metadata, and audio stream info using ffprobe."""
    probe = ffmpeg.probe(input_file, show_chapters=None, show_streams=None, show_format=None)
    chapters = probe.get('chapters', [])
    global_metadata = probe.get('format', {}).get('tags', {})
    # get info
    audio_streams = [stream for stream in probe.get('streams', []) if stream['codec_type'] == 'audio']
    if audio_streams:
        audio_info = audio_streams[0]
        sample_rate = int(audio_info.get('sample_rate', 44100))
    else:
        sample_rate = 44100  # default
    
    return chapters, global_metadata, sample_rate

def process_chapter(args):
    """Process a single chapter."""
    input_file, output_file, start_time, end_time, format, progress_bar, chapter_title, global_metadata, sample_rate = args
    stream = ffmpeg.input(input_file, ss=start_time, t=end_time - start_time)
    
    output_args = {
        'ar': sample_rate,
        'metadata': f"title={chapter_title}",
        'metadata': f"artist={global_metadata.get('artist', '')}",
        'metadata': f"album={global_metadata.get('album', '')}",
    }
    
    if format == 'mp3':
        output_args.update({
            'acodec': 'libmp3lame',
            'ab': '128k',
            'q': 2  # vbr quality
        })
    elif format in ['m4a', 'm4b']:
        output_args.update({
            'acodec': 'aac',
            'b:a': '128k'
        })
    elif format == 'wav':
        output_args.update({
            'acodec': 'pcm_s16le'
        })
    
    # cover art
    cover_data = ffmpeg.probe(input_file, select_streams='v')
    if cover_data.get('streams'):
        output_args['c:v'] = 'copy'
    
    stream = ffmpeg.output(stream, output_file, **output_args)
    ffmpeg.run(stream, quiet=True, overwrite_output=True)
    progress_bar.update(1)

def clean_chapter_title(title):
    """Remove content in parentheses from chapter title."""
    return re.sub(r'\s*\([^)]*\)', '', title).strip()

@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_folder', type=click.Path())
@click.option('--threads', default=os.cpu_count(), help='Number of threads to use')
@click.option('--deduplicate', '-d', is_flag=True, default=True, help='Deduplicate chapters by title (enabled by default)')
@click.option('--format', type=click.Choice(['mp3', 'wav', 'm4a', 'm4b']), default='mp3', help='Export format (default: mp3)')
def main(input_file, output_folder, threads, deduplicate, format):
    chapters, global_metadata, sample_rate = get_file_info(input_file)
    if not chapters:
        click.echo("No chapter information found in the M4B file.")
        return
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    else:
        click.echo(f"Warning: Output folder '{output_folder}' already exists.")
        return

    progress_bar = tqdm(total=len(chapters), desc="Processing chapters")
    
    chapter_args = []
    processed_titles = set()
    deduped_chapters = []

    for i, chapter in enumerate(chapters):
        start_time = float(chapter['start_time'])
        end_time = float(chapter['end_time'])
        title = chapter.get('tags', {}).get('title', f'Chapter_{i+1:03d}')
        clean_title = clean_chapter_title(title)

        if deduplicate:
            if clean_title and clean_title not in processed_titles:
                processed_titles.add(clean_title)
                deduped_chapters.append((i, start_time, end_time, title))
        else:
            deduped_chapters.append((i, start_time, end_time, title))

    num_digits = math.ceil(math.log10(len(deduped_chapters) + 1))

    for i, (chapter_index, start_time, end_time, title) in enumerate(deduped_chapters):
        numbered_title = f"{i+1:0{num_digits}d} - {title}"
        slugified_title = slugify(numbered_title, max_length=100)
        output_file = os.path.join(output_folder, f"{slugified_title}.{format}")
        chapter_args.append((input_file, output_file, start_time, end_time, format, progress_bar, title, global_metadata, sample_rate))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        executor.map(process_chapter, chapter_args)
    
    progress_bar.close()
    
    total_chapters = len(chapters)
    deduped_count = len(deduped_chapters)
    click.echo(f"Successfully processed {total_chapters} chapters.")
    if deduplicate:
        click.echo(f"After deduplication, {deduped_count} unique chapters remain in {output_folder}")
    else:
        click.echo(f"All {deduped_count} chapters saved to {output_folder}")

if __name__ == '__main__':
    main()
