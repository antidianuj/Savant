#!/usr/bin/env python3
"""Run source adapter."""
import os
from typing import List, Optional

import click

from common import (
    adapter_docker_image_option,
    build_common_envs,
    build_docker_run_command,
    fps_meter_options,
    run_command,
    source_id_option,
)


@click.group()
def cli():
    """Click command line group callback."""


sync_option = click.option(
    '--sync',
    is_flag=True,
    default=False,
    help='Send frames from source synchronously (i.e. at the source file rate).',
    show_default=True,
)


def common_options(func):
    """Common Click source adapter options."""
    func = click.option(
        '--out-endpoint',
        default='ipc:///tmp/zmq-sockets/input-video.ipc',
        help='Adapter output (module input) ZeroMQ socket endpoint.',
        show_default=True,
    )(func)
    func = click.option(
        '--out-type',
        default='DEALER',
        help='Adapter output (module input) ZeroMQ socket type.',
        show_default=True,
    )(func)
    func = click.option(
        '--out-bind',
        default=False,
        help=(
            'Adapter output (module input) ZeroMQ socket bind/connect mode '
            '(bind if True).'
        ),
        show_default=True,
    )(func)
    func = fps_meter_options(func)
    func = source_id_option(required=True)(func)
    return func


def files_source(
    source_id: str,
    out_endpoint: str,
    out_type: str,
    out_bind: bool,
    sync: bool,
    docker_image: str,
    fps_period_frames: Optional[int],
    fps_period_seconds: Optional[float],
    fps_output: str,
    location: str,
    file_type: str,
    envs: List[str],
    entrypoint: str = '/opt/savant/adapters/gst/sources/media_files.sh',
    extra_volumes: List[str] = None,
):
    """Read picture or video files from LOCATION.
    LOCATION can be single file, directory or HTTP URL.
    """
    print(source_id)
    if location.startswith('http://') or location.startswith('https://'):
        volumes = []
    else:
        assert os.path.exists(location)
        location = os.path.abspath(location)
        volumes = [f'{location}:{location}:ro']

    if extra_volumes:
        volumes.extend(extra_volumes)

    cmd = build_docker_run_command(
        f'source-{file_type}-files-{source_id}',
        zmq_endpoint=out_endpoint,
        zmq_type=out_type,
        zmq_bind=out_bind,
        sync=sync,
        entrypoint=entrypoint,
        envs=(
            build_common_envs(
                source_id=source_id,
                fps_period_frames=fps_period_frames,
                fps_period_seconds=fps_period_seconds,
                fps_output=fps_output,
            )
            + [f'LOCATION={location}', f'FILE_TYPE={file_type}']
            + envs
        ),
        volumes=volumes,
        docker_image=docker_image,
    )
    run_command(cmd)


@cli.command('videos')
@click.option(
    '--sort-by-time',
    default=False,
    is_flag=True,
    help='Sort files by modification time.',
    show_default=True,
)
@click.option(
    '--read-metadata',
    default=False,
    is_flag=True,
    help='Attempt to read the metadata of objects from the JSON file that has the identical name '
    'as the source file with `json` extension, and then send it to the module.',
    show_default=True,
)
@click.option(
    '--eos-on-file-end',
    help='Send EOS at the end of each file.',
    default=True,
    show_default=True,
)
@common_options
@sync_option
@adapter_docker_image_option('gstreamer')
@click.argument('location', required=True)
def videos_source(
    source_id: str,
    out_endpoint: str,
    out_type: str,
    out_bind: bool,
    sync: bool,
    docker_image: str,
    fps_period_frames: Optional[int],
    fps_period_seconds: Optional[float],
    fps_output: str,
    location: str,
    sort_by_time: bool,
    read_metadata: bool,
    eos_on_file_end: bool,
):
    """Read video files from LOCATION.
    LOCATION can be single file, directory or HTTP URL.
    """
    files_source(
        source_id=source_id,
        out_endpoint=out_endpoint,
        out_type=out_type,
        out_bind=out_bind,
        sync=sync,
        docker_image=docker_image,
        fps_period_frames=fps_period_frames,
        fps_period_seconds=fps_period_seconds,
        fps_output=fps_output,
        location=location,
        file_type='video',
        envs=[
            f'SORT_BY_TIME={sort_by_time}',
            f'READ_METADATA={read_metadata}',
            f'EOS_ON_FILE_END={eos_on_file_end}',
        ],
    )


@cli.command('video-loop')
@click.option(
    '--read-metadata',
    default=False,
    is_flag=True,
    help='Attempt to read the metadata of objects from the JSON file that has the identical name '
    'as the source file with `json` extension, and then send it to the module.',
    show_default=True,
)
@click.option(
    '--eos-on-loop-end',
    default=False,
    is_flag=True,
    help='Send EOS on a loop end.',
    show_default=True,
)
@click.option(
    '--measure-fps-per-loop',
    default=False,
    is_flag=True,
    help='Measure FPS per loop. FPS meter will dump statistics at the end of each loop.',
    show_default=True,
)
@click.option(
    '--download-path',
    default='/tmp/video-loop-source-downloads',
    help='Path to download files from remote storage.',
    show_default=True,
)
@click.option(
    '--mount-download-path',
    default=False,
    is_flag=True,
    help='Mount path to download files from remote storage to the container.',
    show_default=True,
)
@click.option(
    '--loss-rate',
    type=click.FLOAT,
    help='Probability to drop the frames.',
)
@common_options
@sync_option
@adapter_docker_image_option('gstreamer')
@click.argument('location', required=True)
def video_loop_source(
    source_id: str,
    out_endpoint: str,
    out_type: str,
    out_bind: bool,
    sync: bool,
    docker_image: str,
    fps_period_frames: Optional[int],
    fps_period_seconds: Optional[float],
    fps_output: str,
    measure_fps_per_loop: bool,
    eos_on_loop_end: bool,
    download_path: str,
    mount_download_path: bool,
    loss_rate: float,
    location: str,
    read_metadata: bool,
):
    """Read a video file from LOCATION and loop it.
    LOCATION can be single file, directory or HTTP URL.
    """

    download_path = os.path.abspath(download_path)
    if mount_download_path:
        volumes = [f'{download_path}:{download_path}']
    else:
        volumes = []

    envs = [
        f'MEASURE_FPS_PER_LOOP={measure_fps_per_loop}',
        f'EOS_ON_LOOP_END={eos_on_loop_end}',
        f'READ_METADATA={read_metadata}',
        f'DOWNLOAD_PATH={download_path}',
    ]
    if loss_rate is not None:
        envs.append(f'LOSS_RATE={loss_rate}')

    files_source(
        source_id=source_id,
        out_endpoint=out_endpoint,
        out_type=out_type,
        out_bind=out_bind,
        sync=sync,
        docker_image=docker_image,
        fps_period_frames=fps_period_frames,
        fps_period_seconds=fps_period_seconds,
        fps_output=fps_output,
        location=location,
        file_type='video',
        envs=envs,
        entrypoint='/opt/savant/adapters/gst/sources/video_loop.sh',
        extra_volumes=volumes,
    )


@cli.command('pictures')
@click.option(
    '--framerate',
    default='30/1',
    help='Frame rate of the pictures.',
    show_default=True,
)
@click.option(
    '--sort-by-time',
    default=False,
    is_flag=True,
    help='Sort files by modification time.',
    show_default=True,
)
@click.option(
    '--read-metadata',
    default=False,
    is_flag=True,
    help='Attempt to read the metadata of objects from the JSON file that has the identical name '
    'as the source file with `json` extension, and then send it to the module.',
    show_default=True,
)
@click.option(
    '--eos-on-file-end',
    help='Send EOS at the end of each file.',
    default=False,
    show_default=True,
)
@common_options
@sync_option
@adapter_docker_image_option('gstreamer')
@click.argument('location', required=True)
def pictures_source(
    source_id: str,
    out_endpoint: str,
    out_type: str,
    out_bind: bool,
    sync: bool,
    docker_image: str,
    fps_period_frames: Optional[int],
    fps_period_seconds: Optional[float],
    fps_output: str,
    location: str,
    framerate: str,
    sort_by_time: bool,
    read_metadata: bool,
    eos_on_file_end: bool,
):
    """Read picture files from LOCATION.
    LOCATION can be single file, directory or HTTP URL.
    """

    files_source(
        source_id=source_id,
        out_endpoint=out_endpoint,
        out_type=out_type,
        out_bind=out_bind,
        sync=sync,
        docker_image=docker_image,
        fps_period_frames=fps_period_frames,
        fps_period_seconds=fps_period_seconds,
        fps_output=fps_output,
        location=location,
        file_type='picture',
        envs=[
            f'FRAMERATE={framerate}',
            f'SORT_BY_TIME={sort_by_time}',
            f'READ_METADATA={read_metadata}',
            f'EOS_ON_FILE_END={eos_on_file_end}',
        ],
    )


@cli.command('rtsp')
@common_options
@sync_option
@click.option(
    '--sync-delay',
    type=click.INT,
    help=(
        'Delay in seconds before sending frames. '
        'Useful when the source has B-frames to avoid sending frames in batches. '
        'Ignored when synchronous frames sending is turned off (i.e. no --sync flag).'
    ),
)
@click.option(
    '--calculate-dts',
    is_flag=True,
    default=False,
    help='Calculate DTS for frames. Set this flag when the source has B-frames.',
    show_default=True,
)
@adapter_docker_image_option('gstreamer')
@click.argument('rtsp_uri', required=True)
def rtsp_source(
    source_id: str,
    out_endpoint: str,
    out_type: str,
    out_bind: bool,
    sync: bool,
    sync_delay: Optional[int],
    calculate_dts: bool,
    docker_image: str,
    fps_period_frames: Optional[int],
    fps_period_seconds: Optional[float],
    fps_output: str,
    rtsp_uri: str,
):
    """Read video stream from RTSP_URI."""

    envs = build_common_envs(
        source_id=source_id,
        fps_period_frames=fps_period_frames,
        fps_period_seconds=fps_period_seconds,
        fps_output=fps_output,
    ) + [
        f'RTSP_URI={rtsp_uri}',
        f'CALCULATE_DTS={calculate_dts}',
    ]
    if sync and sync_delay is not None:
        envs.append(f'SYNC_DELAY={sync_delay}')

    cmd = build_docker_run_command(
        f'source-rtsp-{source_id}',
        zmq_endpoint=out_endpoint,
        zmq_type=out_type,
        zmq_bind=out_bind,
        sync=sync,
        entrypoint='/opt/savant/adapters/gst/sources/rtsp.sh',
        envs=envs,
        docker_image=docker_image,
    )
    run_command(cmd)


@cli.command('usb-cam')
@click.option(
    '--framerate',
    default='15/1',
    help='USB camera framerate',
    show_default=True,
)
@common_options
@adapter_docker_image_option('gstreamer')
@click.argument('device', default='/dev/video0')
def usb_cam_source(
    source_id: str,
    out_endpoint: str,
    out_type: str,
    out_bind: bool,
    docker_image: str,
    fps_period_frames: Optional[int],
    fps_period_seconds: Optional[float],
    fps_output: str,
    framerate: str,
    device: str,
):
    """Read video stream from USB camera located at DEVICE.

    Default DEVICE: /dev/video0.
    """

    cmd = build_docker_run_command(
        f'source-usb-{source_id}',
        zmq_endpoint=out_endpoint,
        zmq_type=out_type,
        zmq_bind=out_bind,
        entrypoint='/opt/savant/adapters/gst/sources/usb_cam.sh',
        envs=(
            build_common_envs(
                source_id=source_id,
                fps_period_frames=fps_period_frames,
                fps_period_seconds=fps_period_seconds,
                fps_output=fps_output,
            )
            + [f'DEVICE={device}', f'FRAMERATE={framerate}']
        ),
        devices=[device],
        docker_image=docker_image,
    )
    run_command(cmd)


@cli.command('gige')
@click.option('--width', type=int, help='Width of streaming video')
@click.option('--height', type=int, help='Height of streaming video')
@click.option('--framerate', type=str, help='Framerate of streaming video')
@click.option(
    # TODO: replace with PixelFormat
    # https://github.com/AravisProject/aravis/blob/0.8.22/src/arvmisc.c#L656
    '--input-caps',
    type=str,
    help='Caps of input video (e.g. "video/x-raw,format=RGB"). Look '
    'https://github.com/AravisProject/aravis/blob/0.8.22/src/arvmisc.c#L656 '
    'for PixelFormat -> Caps mapping.',
)
@click.option('--packet-size', type=int, help='GigEVision streaming packet size')
@click.option(
    '--auto-packet-size', type=bool, help='Negotiate GigEVision streaming packet size'
)
@click.option('--exposure', type=float, help='Exposure time (µs)')
@click.option('--exposure-auto', help='Auto Exposure Mode, one of "off", "once", "on"')
@click.option('--gain', type=float, help='Gain (dB)')
@click.option('--gain-auto', help='Auto Gain Mode, one of "off", "once", "on"')
@click.option(
    '--features',
    help='Additional configuration parameters as a space separated list of feature assignations',
)
@click.option(
    '--host-network', default=False, is_flag=True, help='Use the host network'
)
@common_options
@adapter_docker_image_option('gstreamer')
@click.argument('camera_name', required=False)
def gige_cam_source(
    source_id: str,
    out_endpoint: str,
    out_type: str,
    out_bind: bool,
    docker_image: str,
    fps_period_frames: Optional[int],
    fps_period_seconds: Optional[float],
    fps_output: str,
    width: Optional[int],
    height: Optional[int],
    framerate: Optional[str],
    input_caps: Optional[str],
    packet_size: Optional[int],
    auto_packet_size: Optional[bool],
    exposure: Optional[float],
    exposure_auto: Optional[str],
    gain: Optional[float],
    gain_auto: Optional[str],
    features: Optional[str],
    host_network: bool,
    camera_name: Optional[str],
):
    """Read video stream from GigE camera CAMERA_NAME.

    If the camera is a GigEVision, CAMERA_NAME can be either:

      - <vendor>-<model>-<serial>

      - <vendor_alias>-<serial>

      - <vendor>-<serial>

      - <user_id>

      - <ip_address>

      - <mac_address>
    """

    envs = build_common_envs(
        source_id=source_id,
        fps_period_frames=fps_period_frames,
        fps_period_seconds=fps_period_seconds,
        fps_output=fps_output,
    )

    if camera_name is not None:
        envs.append(f'CAMERA_NAME={camera_name}')
    if width is not None:
        envs.append(f'WIDTH={width}')
    if height is not None:
        envs.append(f'HEIGHT={height}')
    if framerate is not None:
        envs.append(f'FRAMERATE={framerate}')
    if input_caps is not None:
        envs.append(f'INPUT_CAPS={input_caps}')
    if packet_size is not None:
        envs.append(f'PACKET_SIZE={packet_size}')
    if auto_packet_size is not None:
        envs.append(f'AUTO_PACKET_SIZE={int(auto_packet_size)}')
    if exposure is not None:
        envs.append(f'EXPOSURE={exposure}')
    if exposure_auto is not None:
        envs.append(f'EXPOSURE_AUTO={exposure_auto}')
    if gain is not None:
        envs.append(f'GAIN={gain}')
    if gain_auto is not None:
        envs.append(f'GAIN_AUTO={gain_auto}')
    if features is not None:
        envs.append(f'FEATURES={features}')

    cmd = build_docker_run_command(
        f'source-gige-{source_id}',
        zmq_endpoint=out_endpoint,
        zmq_type=out_type,
        zmq_bind=out_bind,
        entrypoint='/opt/savant/adapters/gst/sources/gige_cam.sh',
        envs=envs,
        docker_image=docker_image,
        host_network=host_network,
    )
    run_command(cmd)


if __name__ == '__main__':
    cli()
