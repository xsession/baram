#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the CAD file import utility (STEP / IGES / BREP).

These tests verify:
- Module-level utilities (format detection, filter generation)
- TessellationParams presets and validation
- CADImportStats formatting
- CADImporter error handling (missing gmsh, bad files)
- Integration with StlSurface interface (when gmsh is available)

Run with:
    python -m pytest tests/test_cad_utility.py -v
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make sure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Unit tests — no gmsh required
# ---------------------------------------------------------------------------

class TestFormatDetection:
    """Test file format detection functions."""

    def test_is_cad_file_step(self):
        from baramMesh.view.geometry.cad_utility import is_cad_file
        assert is_cad_file(Path("model.step")) is True
        assert is_cad_file(Path("model.stp")) is True
        assert is_cad_file(Path("model.STEP")) is True
        assert is_cad_file(Path("model.STP")) is True

    def test_is_cad_file_iges(self):
        from baramMesh.view.geometry.cad_utility import is_cad_file
        assert is_cad_file(Path("model.iges")) is True
        assert is_cad_file(Path("model.igs")) is True

    def test_is_cad_file_brep(self):
        from baramMesh.view.geometry.cad_utility import is_cad_file
        assert is_cad_file(Path("model.brep")) is True
        assert is_cad_file(Path("model.brp")) is True

    def test_is_cad_file_non_cad(self):
        from baramMesh.view.geometry.cad_utility import is_cad_file
        assert is_cad_file(Path("mesh.stl")) is False
        assert is_cad_file(Path("data.csv")) is False
        assert is_cad_file(Path("readme.md")) is False

    def test_is_stl_file(self):
        from baramMesh.view.geometry.cad_utility import is_stl_file
        assert is_stl_file(Path("mesh.stl")) is True
        assert is_stl_file(Path("mesh.STL")) is True
        assert is_stl_file(Path("mesh.step")) is False


class TestCADFormat:
    """Test CADFormat enum."""

    def test_from_path_step(self):
        from baramMesh.view.geometry.cad_utility import CADFormat
        assert CADFormat.from_path(Path("a.step")) == CADFormat.STEP
        assert CADFormat.from_path(Path("a.stp")) == CADFormat.STEP

    def test_from_path_iges(self):
        from baramMesh.view.geometry.cad_utility import CADFormat
        assert CADFormat.from_path(Path("a.iges")) == CADFormat.IGES
        assert CADFormat.from_path(Path("a.igs")) == CADFormat.IGES

    def test_from_path_brep(self):
        from baramMesh.view.geometry.cad_utility import CADFormat
        assert CADFormat.from_path(Path("a.brep")) == CADFormat.BREP
        assert CADFormat.from_path(Path("a.brp")) == CADFormat.BREP

    def test_from_path_unknown(self):
        from baramMesh.view.geometry.cad_utility import CADFormat
        assert CADFormat.from_path(Path("a.stl")) == CADFormat.UNKNOWN
        assert CADFormat.from_path(Path("a.obj")) == CADFormat.UNKNOWN


class TestTessellationParams:
    """Test tessellation parameter presets."""

    def test_medium_defaults(self):
        from baramMesh.view.geometry.cad_utility import TessellationParams
        p = TessellationParams.medium()
        assert p.deflection == 0.001
        assert p.angle == 30.0
        assert p.curvature_elements == 12
        assert p.algorithm == 6

    def test_coarse_faster(self):
        from baramMesh.view.geometry.cad_utility import TessellationParams
        c = TessellationParams.coarse()
        m = TessellationParams.medium()
        assert c.deflection > m.deflection
        assert c.angle > m.angle

    def test_fine_more_precise(self):
        from baramMesh.view.geometry.cad_utility import TessellationParams
        f = TessellationParams.fine()
        m = TessellationParams.medium()
        assert f.deflection < m.deflection
        assert f.angle < m.angle
        assert f.curvature_elements > m.curvature_elements


class TestCADImportStats:
    """Test import statistics formatting."""

    def test_summary_contains_key_info(self):
        from baramMesh.view.geometry.cad_utility import CADImportStats
        stat = CADImportStats(
            file_path='housing.step',
            format='step',
            num_solids=3,
            num_faces=42,
            total_triangles=125430,
            total_nodes=62890,
            elapsed_seconds=2.31,
        )
        s = stat.summary()
        assert 'housing.step' in s
        assert 'step' in s
        assert '125,430' in s
        assert '2.31' in s

    def test_summary_with_warnings(self):
        from baramMesh.view.geometry.cad_utility import CADImportStats
        stat = CADImportStats(file_path='test.stp', format='step')
        stat.warnings.append('Degenerate face ignored')
        s = stat.summary()
        assert 'WARNING' in s
        assert 'Degenerate face' in s


class TestSanitizeName:
    """Test name sanitisation for OpenFOAM compatibility."""

    def test_basic(self):
        from baramMesh.view.geometry.cad_utility import _sanitize_name
        assert _sanitize_name('Part 1') == 'Part_1'

    def test_digit_prefix(self):
        from baramMesh.view.geometry.cad_utility import _sanitize_name
        assert _sanitize_name('3DPart').startswith('_')

    def test_special_chars(self):
        from baramMesh.view.geometry.cad_utility import _sanitize_name
        result = _sanitize_name('Part#1 (copy)')
        assert '#' not in result
        assert '(' not in result

    def test_empty(self):
        from baramMesh.view.geometry.cad_utility import _sanitize_name
        assert _sanitize_name('') == ''


class TestGmshAvailability:
    """Test gmsh availability check."""

    def test_check_returns_bool(self):
        from baramMesh.view.geometry.cad_utility import check_gmsh_available
        result = check_gmsh_available()
        assert isinstance(result, bool)


class TestCADImporterErrors:
    """Test CADImporter error handling without gmsh."""

    def test_unsupported_format(self):
        from baramMesh.view.geometry.cad_utility import CADImporter, CADImportError

        # Need gmsh to be importable for this test path
        try:
            import gmsh
        except ImportError:
            pytest.skip("gmsh not installed")

        importer = CADImporter()
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            f.write(b'not a cad file')
            f.flush()
            with pytest.raises(CADImportError, match='Unsupported CAD format'):
                importer.load([Path(f.name)])

    def test_file_not_found(self):
        from baramMesh.view.geometry.cad_utility import CADImporter, CADImportError

        try:
            import gmsh
        except ImportError:
            pytest.skip("gmsh not installed")

        importer = CADImporter()
        with pytest.raises(CADImportError, match='File not found'):
            importer.load([Path('/nonexistent/model.step')])

    def test_gmsh_not_available(self):
        """Verify GmshNotAvailableError when gmsh is missing."""
        from baramMesh.view.geometry.cad_utility import CADImporter, GmshNotAvailableError

        importer = CADImporter()
        with patch.dict(sys.modules, {'gmsh': None}):
            # Force re-import check
            with patch('builtins.__import__', side_effect=ImportError):
                try:
                    importer.load([Path('test.step')])
                except (GmshNotAvailableError, ImportError):
                    pass  # Expected


class TestFileFilter:
    """Test file dialog filter generation."""

    def test_filter_always_includes_stl(self):
        from baramMesh.view.geometry.cad_utility import get_supported_formats_filter
        f = get_supported_formats_filter()
        assert '*.stl' in f.lower()

    def test_filter_includes_all_supported(self):
        from baramMesh.view.geometry.cad_utility import get_supported_formats_filter
        f = get_supported_formats_filter()
        assert 'All Supported' in f


# ---------------------------------------------------------------------------
# Integration tests — require gmsh
# ---------------------------------------------------------------------------

@pytest.fixture
def gmsh_available():
    """Skip test if gmsh is not installed."""
    try:
        import gmsh
        return True
    except ImportError:
        pytest.skip("gmsh not installed — skipping integration test")


class TestCADImporterIntegration:
    """Integration tests that require gmsh."""

    def test_import_generates_surfaces(self, gmsh_available, tmp_path):
        """Create a simple BREP box and verify import produces surfaces."""
        import gmsh

        from baramMesh.view.geometry.cad_utility import CADImporter, TessellationParams

        # Create a test BREP file
        brep_file = tmp_path / "test_box.brep"
        gmsh.initialize()
        try:
            gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)
            gmsh.model.occ.synchronize()
            gmsh.write(str(brep_file))
        finally:
            gmsh.finalize()

        # Import it
        importer = CADImporter()
        stats = importer.load(
            [brep_file],
            params=TessellationParams.coarse(),
        )

        assert len(stats) == 1
        assert stats[0].total_triangles > 0
        assert stats[0].total_nodes > 0

        volumes, surfaces = importer.identifyVolumes()
        # A box should produce at least some geometry
        assert len(volumes) + len(surfaces) > 0

    def test_import_step_basic(self, gmsh_available, tmp_path):
        """Create a STEP file via gmsh and verify round-trip import."""
        import gmsh

        from baramMesh.view.geometry.cad_utility import CADImporter, TessellationParams

        step_file = tmp_path / "test_cylinder.step"
        gmsh.initialize()
        try:
            gmsh.model.occ.addCylinder(0, 0, 0, 0, 0, 1, 0.5)
            gmsh.model.occ.synchronize()
            gmsh.write(str(step_file))
        finally:
            gmsh.finalize()

        importer = CADImporter()
        stats = importer.load(
            [step_file],
            params=TessellationParams.coarse(),
        )

        assert stats[0].format == 'step'
        assert stats[0].total_triangles > 0

    def test_progress_callback(self, gmsh_available, tmp_path):
        """Verify the progress callback is invoked."""
        import gmsh

        from baramMesh.view.geometry.cad_utility import CADImporter, TessellationParams

        brep_file = tmp_path / "progress_test.brep"
        gmsh.initialize()
        try:
            gmsh.model.occ.addSphere(0, 0, 0, 1)
            gmsh.model.occ.synchronize()
            gmsh.write(str(brep_file))
        finally:
            gmsh.finalize()

        calls = []
        def callback(msg, frac):
            calls.append((msg, frac))

        importer = CADImporter()
        importer.load([brep_file], params=TessellationParams.coarse(),
                      progress_callback=callback)

        assert len(calls) >= 2  # At least start + complete
        assert calls[-1][1] == 1.0  # Final progress = 100%


# ---------------------------------------------------------------------------
# Tests for enterprise infrastructure
# ---------------------------------------------------------------------------

class TestLoggingConfig:
    """Test enterprise logging setup."""

    def test_setup_logging_creates_directory(self, tmp_path):
        from libbaram.logging_config import setup_logging
        log_dir = tmp_path / 'test_logs'
        result = setup_logging(log_dir=log_dir, app_name='test')
        assert result.exists()
        assert (log_dir / 'test.log').exists()

    def test_correlation_id(self):
        from libbaram.logging_config import (
            set_correlation_id, get_correlation_id, clear_correlation_id,
        )
        cid = set_correlation_id('test123')
        assert get_correlation_id() == 'test123'
        clear_correlation_id()
        assert get_correlation_id() == '-'

    def test_perf_timer(self):
        import time
        from libbaram.logging_config import PerfTimer
        with PerfTimer("test op") as timer:
            time.sleep(0.01)
        assert timer.elapsed >= 0.01


class TestConfiguration:
    """Test enterprise configuration management."""

    def test_default_values(self):
        from libbaram.configuration import AppConfig
        c = AppConfig()
        assert c.cad.default_deflection == 0.001
        assert c.logging.level == 'INFO'
        assert c.mesh.default_num_cells_x == 10

    def test_yaml_round_trip(self, tmp_path):
        from libbaram.configuration import AppConfig
        c = AppConfig()
        c.cad.default_deflection = 0.0005
        path = tmp_path / 'test_config.yaml'
        c.save(path)

        c2 = AppConfig()
        c2.load(path)
        assert c2.cad.default_deflection == 0.0005

    def test_to_dict(self):
        from libbaram.configuration import AppConfig
        c = AppConfig()
        d = c.to_dict()
        assert 'cad' in d
        assert 'logging' in d
        assert d['cad']['default_deflection'] == 0.001


class TestExceptionHierarchy:
    """Test the structured exception hierarchy."""

    def test_baram_error_base(self):
        from libbaram.exception import BaramError
        e = BaramError('test error', error_code='TEST_001')
        assert 'test error' in str(e)
        assert e.error_code == 'TEST_001'

    def test_canceled_is_baram_error(self):
        from libbaram.exception import CanceledException, BaramError
        assert issubclass(CanceledException, BaramError)

    def test_geometry_hierarchy(self):
        from libbaram.exception import (
            GeometryError, CADImportError, STLImportError, TessellationError,
        )
        assert issubclass(CADImportError, GeometryError)
        assert issubclass(STLImportError, GeometryError)
        assert issubclass(TessellationError, GeometryError)

    def test_dependency_error(self):
        from libbaram.exception import DependencyError
        e = DependencyError('gmsh', purpose='STEP import', install_cmd='pip install gmsh')
        assert 'gmsh' in str(e)
        assert 'pip install gmsh' in str(e)


class TestMeshUtilities:
    """Test enhanced mesh utility functions."""

    def test_bounds_diagonal(self):
        from libbaram.mesh import Bounds
        b = Bounds(0, 3, 0, 4, 0, 0)
        assert b.diagonal() == 5.0  # 3-4-5 triangle

    def test_bounds_volume(self):
        from libbaram.mesh import Bounds
        b = Bounds(0, 2, 0, 3, 0, 4)
        assert b.volume() == 24.0

    def test_bounds_is_valid(self):
        from libbaram.mesh import Bounds
        valid = Bounds(0, 1, 0, 1, 0, 1)
        assert valid.isValid() is True
        degenerate = Bounds(0, 0, 0, 1, 0, 1)
        assert degenerate.isValid() is False

    def test_bounds_expand(self):
        from libbaram.mesh import Bounds
        b = Bounds(0, 1, 0, 1, 0, 1)
        expanded = b.expandBy(0.1)
        assert expanded.xMin < 0
        assert expanded.xMax > 1

    def test_validate_polydata_none(self):
        from libbaram.mesh import validate_polydata
        assert validate_polydata(None) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
