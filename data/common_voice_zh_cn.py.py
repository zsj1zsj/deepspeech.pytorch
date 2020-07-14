import os
import wget
import tarfile
import argparse
import csv
from multiprocessing.pool import ThreadPool
import subprocess

from deepspeech_pytorch.data.data_opts import add_data_opts
from deepspeech_pytorch.data.utils import create_manifest

parser = argparse.ArgumentParser(description='Downloads and processes Mozilla Common Voice dataset.')
parser = add_data_opts(parser)
parser.add_argument("--target-dir", default='zh-CN/', type=str, help="Directory to store the dataset.")
parser.add_argument("--tar-path", type=str, help="Path to the Common Voice *.tar file if downloaded (Optional).")
parser.add_argument('--files-to-process', default="train.tsv,test.tsv",
                    type=str, help='list of *.tsv file names to process')
args = parser.parse_args()
COMMON_VOICE_URL = "https://voice-prod-bundler-ee1969a6ce8178826482b88e843c335139bd3fb4.s3.amazonaws.com/cv-corpus-5-2020-06-22/zh-CN.tar.gz"


def convert_to_wav(csv_file, target_dir):
    """ Read *.csv file description, convert mp3 to wav, process text.
        Save results to target_dir.
    Args:
        csv_file: str, path to *.csv file with data description, usually start from 'cv-'
        target_dir: str, path to dir to save results; wav/ and txt/ dirs will be created
    """
    wav_dir = os.path.join(target_dir, 'wav/')
    txt_dir = os.path.join(target_dir, 'txt/')
    os.makedirs(wav_dir, exist_ok=True)
    os.makedirs(txt_dir, exist_ok=True)
    path_to_data = os.path.dirname(csv_file)

    def process(x):
        file_path, text = x
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        text = text.strip().upper()
        with open(os.path.join(txt_dir, file_name + '.txt'), 'w') as f:
            f.write(text)
        cmd = "sox {} -r {} -b 16 -c 1 {}".format(
            os.path.join(path_to_data, file_path),
            args.sample_rate,
            os.path.join(wav_dir, file_name + '.wav'))
        subprocess.call([cmd], shell=True)

    print('Converting mp3 to wav for {}.'.format(csv_file))
    with open(csv_file) as csvfile:
        data = [(row['path'], row['sentence']) for row in reader]
        reader = csv.DictReader(csvfile)
        with ThreadPool(10) as pool:
            pool.map(process, data)


def main():
    target_dir = args.target_dir
    os.makedirs(target_dir, exist_ok=True)

    target_unpacked_dir = os.path.join(target_dir, "cv-corpus-5-2020-06-22/")
    os.makedirs(target_unpacked_dir, exist_ok=True)

    if args.tar_path and os.path.exists(args.tar_path):
        print('Find existing file {}'.format(args.tar_path))
        target_file = args.tar_path
    else:
        print("Could not find downloaded Common Voice archive, Downloading corpus...")
        filename = wget.download(COMMON_VOICE_URL, target_dir)
        target_file = os.path.join(target_dir, os.path.basename(filename))

    print("Unpacking corpus to {} ...".format(target_unpacked_dir))
    tar = tarfile.open(target_file)
    tar.extractall(target_unpacked_dir)
    tar.close()

    for csv_file in args.files_to_process.split(','):
        convert_to_wav(os.path.join(target_unpacked_dir, 'zh-CN/', csv_file),
                       os.path.join(target_dir, os.path.splitext(csv_file)[0]))

    print('Creating manifests...')
    for csv_file in args.files_to_process.split(','):
        create_manifest(data_path=os.path.join(target_dir, os.path.splitext(csv_file)[0]),
                        output_name=os.path.splitext(csv_file)[0] + '_manifest.csv',
                        manifest_path=args.manifest_dir,
                        min_duration=args.min_duration,
                        max_duration=args.max_duration)


if __name__ == "__main__":
    main()
