from distutils.core import setup
import glob

__version__ = '0.0.0'

setup(name='mkat_fpga_tests',
    version=__version__,
    description='Tests for MeerKAT signal processing FPGAs ',
    license='GPL',
    author='SKA SA DBE Team',
    author_email='paulp at ska.ac.za',
    url='https://github.com/ska-sa/mkat_fpga',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Radio Telescope correlator builders',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Topic :: Scientific/Engineering :: Astronomy',
        ],
    install_requires=['casperfpga', 'corr2', 'katcp', 'matplotlib', 'iniparse', 'numpy', 'spead', 'h5py'],
    provides=['mkat_fpga_tests'],
    packages=['mkat_fpga_tests'],
    scripts=glob.glob('scripts/*')
)

# end
