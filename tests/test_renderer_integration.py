"""
测试渲染器集成模块
"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock


class TestLayeredRenderer:
    """测试差分立绘渲染器"""
    
    def test_import(self):
        """测试模块导入"""
        from higanvn.engine.layered_renderer import (
            LayeredCharacterRenderer,
            CompositeCache,
            AssetLoader,
        )
    
    def test_composite_cache_basic(self):
        """测试合成缓存基本操作"""
        from higanvn.engine.layered_renderer import CompositeCache
        
        cache = CompositeCache(max_entries=10)
        
        # 创建模拟 Surface
        mock_surface = Mock()
        mock_surface.get_size.return_value = (100, 100)
        mock_surface.get_bytesize.return_value = 4
        mock_surface.get_width.return_value = 100
        mock_surface.get_height.return_value = 100
        
        # 缓存未命中
        assert cache.get("test_key") is None
        assert cache.misses == 1
        
        # 放入缓存
        cache.put("test_key", mock_surface)
        
        # 缓存命中
        result = cache.get("test_key")
        assert result is mock_surface
        assert cache.hits == 1
    
    def test_composite_cache_eviction(self):
        """测试缓存淘汰"""
        from higanvn.engine.layered_renderer import CompositeCache
        
        cache = CompositeCache(max_entries=3)
        
        for i in range(5):
            mock = Mock()
            mock.get_size.return_value = (10, 10)
            mock.get_bytesize.return_value = 4
            mock.get_width.return_value = 10
            mock.get_height.return_value = 10
            cache.put(f"key_{i}", mock)
        
        # 应该只保留最近的 3 个
        assert len(cache._cache) <= 3
        assert cache.evictions > 0
    
    def test_composite_cache_invalidate(self):
        """测试缓存失效"""
        from higanvn.engine.layered_renderer import CompositeCache
        
        cache = CompositeCache()
        
        mock = Mock()
        mock.get_size.return_value = (10, 10)
        mock.get_bytesize.return_value = 4
        mock.get_width.return_value = 10
        mock.get_height.return_value = 10
        
        cache.put("alice:normal:happy:school:", mock)
        cache.put("alice:normal:sad:school:", mock)
        cache.put("bob:normal:happy:default:", mock)
        
        # 使 alice 相关缓存失效
        removed = cache.invalidate("alice")
        assert removed == 2
        assert len(cache._cache) == 1
    
    def test_composite_cache_stats(self):
        """测试缓存统计"""
        from higanvn.engine.layered_renderer import CompositeCache
        
        cache = CompositeCache(max_bytes=1024*1024)
        
        mock = Mock()
        mock.get_size.return_value = (10, 10)
        mock.get_bytesize.return_value = 4
        mock.get_width.return_value = 10
        mock.get_height.return_value = 10
        
        cache.put("test", mock)
        cache.get("test")
        cache.get("missing")
        
        stats = cache.stats()
        assert stats["entries"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
    
    def test_layered_renderer_init(self):
        """测试渲染器初始化"""
        from higanvn.engine.layered_renderer import LayeredCharacterRenderer
        
        renderer = LayeredCharacterRenderer()
        assert renderer._manifests == {}
        assert renderer._states == {}
    
    def test_layered_renderer_with_manifest(self):
        """测试带 manifest 的渲染器"""
        from higanvn.engine.layered_renderer import LayeredCharacterRenderer
        from higanvn.packaging.layered_sprite import CharacterSpriteManifest
        
        with tempfile.TemporaryDirectory() as tmpdir:
            chars_dir = Path(tmpdir)
            alice_dir = chars_dir / "alice"
            alice_dir.mkdir()
            
            # 创建简单 manifest
            manifest = CharacterSpriteManifest(
                id="alice",
                name="Alice",
            )
            manifest.save(alice_dir / "manifest.json")
            
            # 初始化渲染器
            renderer = LayeredCharacterRenderer(characters_dir=chars_dir)
            
            assert renderer.has_manifest("alice")
            assert not renderer.has_manifest("bob")
    
    def test_layered_renderer_state(self):
        """测试渲染器状态管理"""
        from higanvn.engine.layered_renderer import LayeredCharacterRenderer
        
        renderer = LayeredCharacterRenderer()
        
        # 设置状态
        state = renderer.set_state(
            "test",
            pose="normal",
            expression="happy",
            outfit="school",
        )
        
        assert state.character_id == "test"
        assert state.pose == "normal"
        assert state.expression == "happy"
        assert state.outfit == "school"
        
        # 更新状态
        state = renderer.set_state("test", expression="sad")
        assert state.expression == "sad"
        assert state.pose == "normal"  # 保持不变
    
    def test_layered_renderer_effects(self):
        """测试特效管理"""
        from higanvn.engine.layered_renderer import LayeredCharacterRenderer
        
        renderer = LayeredCharacterRenderer()
        renderer.set_state("test")
        
        renderer.add_effect("test", "blush")
        state = renderer.get_state("test")
        assert "blush" in state.active_effects
        
        renderer.add_effect("test", "sweat")
        assert len(state.active_effects) == 2
        
        renderer.remove_effect("test", "blush")
        assert "blush" not in state.active_effects
        
        renderer.clear_effects("test")
        assert len(state.active_effects) == 0


class TestAssetLoader:
    """测试资源加载器"""
    
    def test_import(self):
        """测试导入"""
        from higanvn.engine.layered_renderer import AssetLoader
    
    def test_loader_init(self):
        """测试初始化"""
        from higanvn.engine.layered_renderer import AssetLoader
        
        loader = AssetLoader()
        assert loader.loads == 0
        assert loader.cache_hits == 0
    
    def test_loader_exists(self):
        """测试文件存在检查"""
        from higanvn.engine.layered_renderer import AssetLoader
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "test.txt").write_text("hello")
            
            loader = AssetLoader(base_dir=base_dir)
            
            assert loader.exists("test.txt")
            assert not loader.exists("missing.txt")
    
    def test_loader_load_bytes(self):
        """测试加载字节"""
        from higanvn.engine.layered_renderer import AssetLoader
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "data.bin").write_bytes(b"binary data")
            
            loader = AssetLoader(base_dir=base_dir)
            
            data = loader.load_bytes("data.bin")
            assert data == b"binary data"
            
            assert loader.load_bytes("missing.bin") is None
    
    def test_loader_stats(self):
        """测试统计"""
        from higanvn.engine.layered_renderer import AssetLoader
        
        loader = AssetLoader()
        stats = loader.stats()
        
        assert "loads" in stats
        assert "cache_hits" in stats
        assert "cache_entries" in stats


class TestEnhancedCharacterLayer:
    """测试增强角色图层"""
    
    def test_import(self):
        """测试导入"""
        from higanvn.engine.enhanced_characters import EnhancedCharacterLayer
    
    def test_init(self):
        """测试初始化"""
        from higanvn.engine.enhanced_characters import EnhancedCharacterLayer
        
        layer = EnhancedCharacterLayer(slots={})
        
        assert layer.characters == {}
        assert layer.active_actor is None
    
    def test_traditional_mode(self):
        """测试传统模式"""
        from higanvn.engine.enhanced_characters import EnhancedCharacterLayer
        
        layer = EnhancedCharacterLayer(slots={})
        
        # 没有 manifest，应该使用传统模式
        assert not layer._is_layered("alice")
    
    def test_layered_mode_detection(self):
        """测试差分模式检测"""
        from higanvn.engine.enhanced_characters import EnhancedCharacterLayer
        from higanvn.packaging.layered_sprite import CharacterSpriteManifest
        
        with tempfile.TemporaryDirectory() as tmpdir:
            chars_dir = Path(tmpdir)
            alice_dir = chars_dir / "alice"
            alice_dir.mkdir()
            
            manifest = CharacterSpriteManifest(id="alice", name="Alice")
            manifest.save(alice_dir / "manifest.json")
            
            layer = EnhancedCharacterLayer(
                slots={},
                characters_dir=chars_dir,
            )
            
            # alice 有 manifest，应该使用差分模式
            assert layer._is_layered("alice")
            # bob 没有 manifest
            assert not layer._is_layered("bob")
    
    def test_set_outfit(self):
        """测试设置服装"""
        from higanvn.engine.enhanced_characters import EnhancedCharacterLayer
        
        layer = EnhancedCharacterLayer(slots={})
        
        layer.set_outfit("alice", "school")
        assert layer._outfits["alice"] == "school"
        
        layer.set_outfit("alice", None)
        assert layer._outfits["alice"] is None
    
    def test_remove_clear(self):
        """测试移除和清除"""
        from higanvn.engine.enhanced_characters import EnhancedCharacterLayer
        
        layer = EnhancedCharacterLayer(slots={})
        
        # 模拟添加角色
        layer.characters["alice"] = (Mock(), None)
        layer.characters["bob"] = (Mock(), None)
        layer.active_actor = "alice"
        
        layer.remove("alice")
        assert "alice" not in layer.characters
        assert layer.active_actor is None
        
        layer.clear()
        assert len(layer.characters) == 0
    
    def test_snapshot(self):
        """测试快照"""
        from higanvn.engine.enhanced_characters import EnhancedCharacterLayer
        
        layer = EnhancedCharacterLayer(slots={})
        
        layer.characters["alice"] = (Mock(), Mock())
        layer._outfits["alice"] = "school"
        layer._pose_names["alice"] = "happy"
        
        snapshot = layer.snapshot_characters()
        
        assert len(snapshot) == 1
        assert snapshot[0]["id"] == "alice"
        assert snapshot[0]["outfit"] == "school"
        assert snapshot[0]["pose"] == "happy"
    
    def test_cache_stats(self):
        """测试缓存统计"""
        from higanvn.engine.enhanced_characters import EnhancedCharacterLayer
        
        layer = EnhancedCharacterLayer(slots={})
        
        stats = layer.cache_stats()
        
        assert "traditional_characters" in stats
        assert "layered_mode" in stats
    
    def test_effects_management(self):
        """测试特效管理"""
        from higanvn.engine.enhanced_characters import EnhancedCharacterLayer
        from higanvn.packaging.layered_sprite import CharacterSpriteManifest
        
        with tempfile.TemporaryDirectory() as tmpdir:
            chars_dir = Path(tmpdir)
            alice_dir = chars_dir / "alice"
            alice_dir.mkdir()
            
            manifest = CharacterSpriteManifest(id="alice", name="Alice")
            manifest.save(alice_dir / "manifest.json")
            
            layer = EnhancedCharacterLayer(
                slots={},
                characters_dir=chars_dir,
            )
            
            # 初始化状态
            layer._layered_renderer.set_state("alice")
            
            # 添加特效
            layer.add_effect("alice", "blush")
            state = layer._layered_renderer.get_state("alice")
            assert "blush" in state.active_effects
            
            # 移除特效
            layer.remove_effect("alice", "blush")
            assert "blush" not in state.active_effects
    
    def test_pose_parsing(self):
        """测试表情解析（复合格式）"""
        from higanvn.engine.enhanced_characters import EnhancedCharacterLayer
        from higanvn.packaging.layered_sprite import (
            CharacterSpriteManifest,
            PoseDefinition,
            ExpressionDefinition,
            LayerDefinition,
            LayerType,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            chars_dir = Path(tmpdir)
            alice_dir = chars_dir / "alice"
            alice_dir.mkdir()
            
            # 创建有姿势和表情的 manifest
            manifest = CharacterSpriteManifest(id="alice", name="Alice")
            manifest.poses["normal"] = PoseDefinition(id="normal", base_layer="base")
            manifest.poses["sit"] = PoseDefinition(id="sit", base_layer="base_sit")
            manifest.expressions["happy"] = ExpressionDefinition(id="happy")
            manifest.expressions["sad"] = ExpressionDefinition(id="sad")
            manifest.save(alice_dir / "manifest.json")
            
            layer = EnhancedCharacterLayer(
                slots={},
                characters_dir=chars_dir,
            )
            
            # 测试复合格式 "pose:expression"
            layer.set_pose("alice", "sit:happy", lambda x: x, lambda x: Mock())
            
            state = layer._layered_renderer.get_state("alice")
            assert state.pose == "sit"
            assert state.expression == "happy"
            
            # 测试简单格式（当没有匹配的 pose 时作为 expression）
            layer.set_pose("alice", "sad", lambda x: x, lambda x: Mock())
            
            state = layer._layered_renderer.get_state("alice")
            assert state.expression == "sad"
    
    def test_effects_in_pose_string(self):
        """测试表情字符串中的特效"""
        from higanvn.engine.enhanced_characters import EnhancedCharacterLayer
        from higanvn.packaging.layered_sprite import CharacterSpriteManifest
        
        with tempfile.TemporaryDirectory() as tmpdir:
            chars_dir = Path(tmpdir)
            alice_dir = chars_dir / "alice"
            alice_dir.mkdir()
            
            manifest = CharacterSpriteManifest(id="alice", name="Alice")
            manifest.save(alice_dir / "manifest.json")
            
            layer = EnhancedCharacterLayer(
                slots={},
                characters_dir=chars_dir,
            )
            
            # 测试 "expression+effect" 格式
            layer.set_pose("alice", "shy+blush", lambda x: x, lambda x: Mock())
            
            state = layer._layered_renderer.get_state("alice")
            assert state.expression == "shy"
            assert "blush" in state.active_effects


class TestIntegration:
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流"""
        from higanvn.engine.enhanced_characters import EnhancedCharacterLayer
        from higanvn.engine.layered_renderer import AssetLoader
        from higanvn.packaging.layered_sprite import (
            CharacterSpriteManifest,
            PoseDefinition,
            ExpressionDefinition,
            OutfitDefinition,
            LayerDefinition,
            LayerType,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            chars_dir = Path(tmpdir)
            alice_dir = chars_dir / "alice"
            alice_dir.mkdir()
            
            # 创建完整的 manifest
            manifest = CharacterSpriteManifest(
                id="alice",
                name="Alice",
                canvas_width=512,
                canvas_height=768,
            )
            
            # 添加图层
            manifest.layers["base_normal"] = LayerDefinition(
                id="base_normal",
                layer_type=LayerType.BASE,
                file="base/normal.png",
                z_order=0,
            )
            manifest.layers["face_happy"] = LayerDefinition(
                id="face_happy",
                layer_type=LayerType.FACE_COMPOSITE,
                file="face/happy.png",
                z_order=100,
            )
            
            manifest.poses["normal"] = PoseDefinition(
                id="normal",
                base_layer="base_normal",
            )
            manifest.expressions["happy"] = ExpressionDefinition(
                id="happy",
                composite_layer="face_happy",
            )
            manifest.outfits["school"] = OutfitDefinition(
                id="school",
                layers=[],
            )
            
            manifest.save(alice_dir / "manifest.json")
            
            # 创建资源加载器
            loader = AssetLoader(base_dir=chars_dir)
            
            # 创建增强角色图层
            layer = EnhancedCharacterLayer(
                slots={},
                characters_dir=chars_dir,
                asset_loader=loader,
            )
            
            # 验证差分模式
            assert layer._is_layered("alice")
            
            # 设置状态
            layer.set_pose("alice", "normal:happy:school", lambda x: x, lambda x: Mock())
            
            # 验证状态
            state = layer._layered_renderer.get_state("alice")
            assert state.pose == "normal"
            assert state.expression == "happy"
            assert state.outfit == "school"
            
            # 获取快照
            snapshot = layer.snapshot_characters()
            assert len(snapshot) == 1
            assert snapshot[0]["layered"] is True
            assert "layered_state" in snapshot[0]
