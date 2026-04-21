from setuptools import setup, Extension
import pybind11

ext_modules = [
    Extension(
        "sunycore_native",
        ["suny_core/native/sunycore.cpp"],
        include_dirs=[pybind11.get_include()],
        language="c++",
        extra_compile_args=["-O3"],
    )
]

setup(
    name="sunycore-native",
    version="0.1.0",
    ext_modules=ext_modules,
    zip_safe=False,
)

