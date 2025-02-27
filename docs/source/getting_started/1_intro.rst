Introduction
============

Getting Started Tutorials
-------------------------

We created several tutorials to help you get started with Savant. These tutorials are designed for both x86+dGPU, and Jetson NX/AGX+ edge devices.

The tutorials are published on Medium:

- `Meet Savant: a New High-Performance Python Video Analytics Framework For Nvidia Hardware <https://hello.savant.video/peoplenet-tutorial>`_;
- `Building a 500+ FPS Accelerated Video Background Removal Pipeline with Savant and OpenCV CUDA MOG2 <https://hello.savant.video/opencv-cuda-bg-remover-mog2-tutorial>`_;
- `Building a High-Performance Car Classification Pipeline With Savant <https://medium.com/inside-in-sight/building-a-high-performance-car-classifier-pipeline-with-savant-b232461ad96?source=friends_link&sk=63cb289315679af83032ef5247861a2d>`_.

Savant simplifies everyday tasks, including data ingestion, stream processing, data output, and other operations encountered when building video analytics pipelines. With GStreamer technicalities being hidden by Savant, all the user writes is code and configuration specific to their video analytics application.

How The Pipeline Looks Like
---------------------------

Every Savant application consists of two parts: YAML configuration and Python code. The configuration is used to define the pipeline, and the Python code is used to implement custom processing.

Let's take a look at a few pieces of YAML serving specific purposes; later in the documentation, we will explore them in detail. There are essential omitted parts in every unit provided in the following code snippets; this is done with the intention of not overwhelming readers with details.

We begin with a pipeline containing one unit - a detector:

.. code-block:: yaml

  pipeline:
    elements:
      - element: nvinfer@detector
        name: primary_detector
        output:
          objects:
            - class_id: 0
              label: car

Next, add a classifier model to the pipeline, which is used to classify cars into different colors:

.. code-block:: yaml

  elements:
    - element: nvinfer@detector
      name: primary_detector
      output:
        objects:
          - class_id: 0
            label: car
    - element: nvinfer@attribute_model
      name: secondary_carcolor
      input:
        objects: primary_detector.car
      output:
        attributes:
          - name: car_color

Next, add custom processing in Python, e.g., count the number of detected cars of each color:

.. code-block:: yaml

  elements:
    - element: nvinfer@detector
      name: primary_detector
      output:
        objects:
          - class_id: 0
            label: car
    - element: nvinfer@attribute_model
      name: secondary_carcolor
      input:
        objects: primary_detector.car
      output:
        attributes:
          - name: car_color
    - element: pyfunc
      name: car_counter
      module: module.car_counter
      class_name: CarCounter

The contents of ``module/car_counter.py`` would be:

.. code-block:: python

    from collections import Counter
    from savant.deepstream.meta.frame import NvDsFrameMeta
    from savant.deepstream.pyfunc import NvDsPyFuncPlugin

    counter = Counter()

    CAR_COLOR_ELEMENT_NAME = 'secondary_carcolor'
    CAR_COLOR_ATTR_NAME = 'car_color'

    class CarCounter(NvDsPyFuncPlugin):
        def process_frame(self, buffer: Gst.Buffer, frame_meta: NvDsFrameMeta):
            for obj_meta in frame_meta.objects:
                car_color_attr = obj_meta.get_attr_meta(CAR_COLOR_ELEMENT_NAME, CAR_COLOR_ATTR_NAME)
                counter[car_color_attr.value] += 1

This is what a typical Savant pipeline looks like. Other examples of pipelines can be found in the `examples <https://github.com/insight-platform/Savant/tree/develop/samples>`_ directory.
