"""
Tests for Asset Pack System
"""
import pytest
import json
import tempfile
from pathlib import Path


class TestAssetPackSystem:
    """Test asset pack system."""
    
    def test_import_modules(self):
        """Test that all modules can be imported."""
        from higanvn.packaging.asset_pack import (
            AssetType, AssetEntry, CharacterDefinition,
            BackgroundDefinition, CGDefinition, PackManifest,
            AssetPackBuilder, AssetPackLoader,
        )
        assert AssetType is not None
        assert AssetEntry is not None
        assert PackManifest is not None
    
    def test_asset_type_enum(self):
        """Test AssetType enum values."""
        from higanvn.packaging.asset_pack import AssetType
        
        assert AssetType.CHARACTER.value == 1
        assert AssetType.BACKGROUND.value == 2
        assert AssetType.BGM.value == 5
        assert AssetType.VOICE.value == 7
    
    def test_asset_entry_creation(self):
        """Test AssetEntry creation."""
        from higanvn.packaging.asset_pack import AssetEntry, AssetType
        
        entry = AssetEntry(
            path="characters/test/base.png",
            asset_type=AssetType.CHARACTER,
            size=1024,
            hash_md5="abc123",
        )
        
        assert entry.path == "characters/test/base.png"
        assert entry.asset_type == AssetType.CHARACTER
        assert entry.size == 1024
    
    def test_asset_entry_serialization(self):
        """Test AssetEntry serialization."""
        from higanvn.packaging.asset_pack import AssetEntry, AssetType
        
        entry = AssetEntry(
            path="bg/test.jpg",
            asset_type=AssetType.BACKGROUND,
            size=2048,
        )
        
        d = entry.to_dict()
        assert d['path'] == "bg/test.jpg"
        assert d['asset_type'] == 2  # BACKGROUND = 2
        
        # Deserialize
        entry2 = AssetEntry.from_dict(d)
        assert entry2.path == entry.path
        assert entry2.asset_type == entry.asset_type
    
    def test_character_definition(self):
        """Test CharacterDefinition creation."""
        from higanvn.packaging.asset_pack import CharacterDefinition
        
        char = CharacterDefinition(
            id="test_char",
            name="Test Character",
            expressions=["normal", "happy"],
            outfits=["school", "casual"],
        )
        
        assert char.id == "test_char"
        assert "happy" in char.expressions
        assert "school" in char.outfits
    
    def test_pack_manifest_serialization(self):
        """Test PackManifest JSON serialization."""
        from higanvn.packaging.asset_pack import (
            PackManifest, AssetEntry, AssetType,
            CharacterDefinition, BackgroundDefinition,
        )
        
        manifest = PackManifest(
            name="test_pack",
            version="1.0.0",
            author="Test Author",
        )
        
        manifest.characters["test"] = CharacterDefinition(
            id="test",
            name="Test Char",
        )
        
        manifest.entries["bg/test.jpg"] = AssetEntry(
            path="bg/test.jpg",
            asset_type=AssetType.BACKGROUND,
            size=1024,
        )
        
        # Serialize
        json_str = manifest.to_json()
        data = json.loads(json_str)
        
        assert data['name'] == "test_pack"
        assert 'test' in data['characters']
        assert 'bg/test.jpg' in data['entries']
        
        # Deserialize
        manifest2 = PackManifest.from_json(json_str)
        assert manifest2.name == manifest.name
        assert 'test' in manifest2.characters
    
    def test_asset_pack_builder_init(self):
        """Test AssetPackBuilder initialization."""
        from higanvn.packaging.asset_pack import AssetPackBuilder
        
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = AssetPackBuilder(Path(tmpdir), "test")
            assert builder.pack_name == "test"
            assert builder.source_dir == Path(tmpdir)
    
    def test_asset_pack_builder_scan_empty(self):
        """Test scanning empty directory."""
        from higanvn.packaging.asset_pack import AssetPackBuilder
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create standard directories
            for subdir in ['characters', 'backgrounds', 'cg']:
                (Path(tmpdir) / subdir).mkdir()
            
            builder = AssetPackBuilder(Path(tmpdir), "test")
            manifest = builder.scan()
            
            assert manifest.total_files == 0
    
    def test_asset_pack_loader_init(self):
        """Test AssetPackLoader initialization."""
        from higanvn.packaging.asset_pack import AssetPackLoader
        
        loader = AssetPackLoader()
        assert loader.packs == []
        loader.close()
    
    def test_asset_pack_loader_list_empty(self):
        """Test listing from empty loader."""
        from higanvn.packaging.asset_pack import AssetPackLoader
        
        loader = AssetPackLoader()
        
        assert loader.list_characters() == {}
        assert loader.list_backgrounds() == {}
        assert loader.list_cgs() == {}
        
        loader.close()
    
    def test_global_functions(self):
        """Test global convenience functions."""
        from higanvn.packaging.asset_pack import (
            get_asset_loader, init_asset_loader,
        )
        
        loader = init_asset_loader()
        assert loader is not None
        assert get_asset_loader() is loader


class TestGameConfig:
    """Test game configuration system."""
    
    def test_import(self):
        """Test importing game config module."""
        from higanvn.packaging.game_config import (
            GameConfig, GameMetadata, ActorDefinition,
            GalleryConfig, GalleryCategory,
        )
        assert GameConfig is not None
        assert GameMetadata is not None
    
    def test_game_metadata_defaults(self):
        """Test GameMetadata default values."""
        from higanvn.packaging.game_config import GameMetadata
        
        meta = GameMetadata()
        assert meta.title == "Untitled Game"
        assert meta.width == 1280
        assert meta.height == 720
        assert meta.enable_gallery is True
        assert meta.save_slots == 20
    
    def test_actor_definition(self):
        """Test ActorDefinition creation."""
        from higanvn.packaging.game_config import ActorDefinition
        
        actor = ActorDefinition(
            id="test",
            name="Test Actor",
            name_color="#FF0000",
            is_protagonist=True,
        )
        
        assert actor.id == "test"
        assert actor.name_color == "#FF0000"
        assert actor.is_protagonist is True
    
    def test_game_config_serialization(self):
        """Test GameConfig JSON serialization."""
        from higanvn.packaging.game_config import (
            GameConfig, GameMetadata, ActorDefinition,
        )
        
        config = GameConfig()
        config.metadata.title = "Test Game"
        config.actors["test"] = ActorDefinition(
            id="test",
            name="Test Char",
        )
        
        json_str = config.to_json()
        data = json.loads(json_str)
        
        assert data['metadata']['title'] == "Test Game"
        assert 'test' in data['actors']
        
        # Deserialize
        config2 = GameConfig.from_json(json_str)
        assert config2.metadata.title == "Test Game"
        assert 'test' in config2.actors
    
    def test_game_config_save_load(self):
        """Test GameConfig save and load."""
        from higanvn.packaging.game_config import GameConfig, ActorDefinition
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = GameConfig()
            config.metadata.title = "Save Test"
            config.actors["hero"] = ActorDefinition(id="hero", name="Hero")
            
            path = Path(tmpdir) / "game.json"
            config.save(path)
            
            assert path.exists()
            
            loaded = GameConfig.load(path)
            assert loaded.metadata.title == "Save Test"
            assert "hero" in loaded.actors
    
    def test_get_actor_by_name(self):
        """Test finding actor by name."""
        from higanvn.packaging.game_config import GameConfig, ActorDefinition
        
        config = GameConfig()
        config.actors["test_id"] = ActorDefinition(
            id="test_id",
            name="Display Name",
            aliases=["Alias1", "Alias2"],
        )
        
        # By ID
        assert config.get_actor_by_name("test_id") is not None
        
        # By display name
        actor = config.get_actor_by_name("Display Name")
        assert actor is not None
        assert actor.id == "test_id"
        
        # By alias
        actor = config.get_actor_by_name("Alias1")
        assert actor is not None
        assert actor.id == "test_id"
        
        # Not found
        assert config.get_actor_by_name("Unknown") is None


class TestProjectTemplate:
    """Test project template system."""
    
    def test_import(self):
        """Test importing project template module."""
        from higanvn.packaging.project_template import (
            create_project, create_character,
            migrate_legacy_project, validate_project,
        )
        assert create_project is not None
    
    def test_create_project(self):
        """Test creating new project."""
        from higanvn.packaging.project_template import create_project
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project(
                Path(tmpdir) / "test_game",
                title="Test Game",
                author="Test Author",
            )
            
            assert project_dir.exists()
            assert (project_dir / "config" / "game.json").exists()
            assert (project_dir / "scripts" / "main.vns").exists()
            assert (project_dir / "assets").exists()
            assert (project_dir / "README.md").exists()
    
    def test_create_project_structure(self):
        """Test that created project has correct structure."""
        from higanvn.packaging.project_template import create_project
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project(Path(tmpdir) / "test", title="Test")
            
            # Check directories
            assert (project_dir / "assets" / "characters").exists()
            assert (project_dir / "assets" / "backgrounds").exists()
            assert (project_dir / "assets" / "audio" / "bgm").exists()
            assert (project_dir / "scripts" / "chapters").exists()
    
    def test_create_character(self):
        """Test creating character directory."""
        from higanvn.packaging.project_template import create_project, create_character
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project(Path(tmpdir) / "test", title="Test")
            
            char_dir = create_character(
                project_dir,
                actor_id="hero",
                display_name="Hero",
                expressions=["normal", "happy", "angry"],
            )
            
            assert char_dir.exists()
            assert (char_dir / "expressions").exists()
            assert (char_dir / "manifest.json").exists()
    
    def test_validate_project(self):
        """Test project validation."""
        from higanvn.packaging.project_template import create_project, validate_project
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project(Path(tmpdir) / "test", title="Test")
            
            result = validate_project(project_dir)
            
            assert result["valid"] is True
            assert len(result["errors"]) == 0
    
    def test_validate_invalid_project(self):
        """Test validation of invalid project."""
        from higanvn.packaging.project_template import validate_project
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Empty directory
            result = validate_project(Path(tmpdir))
            
            assert result["valid"] is False
            assert len(result["errors"]) > 0
