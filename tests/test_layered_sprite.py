"""
测试差分立绘系统和分包加密系统
"""
import pytest
import json
import tempfile
from pathlib import Path


class TestLayeredSpriteSystem:
    """测试差分立绘系统"""
    
    def test_import(self):
        """测试模块导入"""
        from higanvn.packaging.layered_sprite import (
            LayerType,
            BlendMode,
            LayerDefinition,
            PoseDefinition,
            ExpressionDefinition,
            OutfitDefinition,
            CharacterSpriteManifest,
            SpriteState,
            SpriteCompositor,
        )
    
    def test_layer_type_enum(self):
        """测试图层类型枚举"""
        from higanvn.packaging.layered_sprite import LayerType
        
        assert LayerType.BASE.value == 0
        assert LayerType.FACE_COMPOSITE.value == 14
        assert LayerType.EFFECT.value == 20
    
    def test_layer_definition(self):
        """测试图层定义"""
        from higanvn.packaging.layered_sprite import LayerDefinition, LayerType, BlendMode
        
        layer = LayerDefinition(
            id="base_normal",
            layer_type=LayerType.BASE,
            file="base/normal.png",
            z_order=0,
        )
        
        assert layer.id == "base_normal"
        assert layer.layer_type == LayerType.BASE
        assert layer.opacity == 1.0
        
        # 序列化
        d = layer.to_dict()
        assert d['id'] == "base_normal"
        assert d['layer_type'] == "BASE"
        
        # 反序列化
        layer2 = LayerDefinition.from_dict(d)
        assert layer2.id == layer.id
        assert layer2.layer_type == layer.layer_type
    
    def test_expression_definition(self):
        """测试表情定义"""
        from higanvn.packaging.layered_sprite import ExpressionDefinition
        
        # 整合模式
        expr1 = ExpressionDefinition(
            id="happy",
            composite_layer="face_happy",
        )
        assert expr1.composite_layer == "face_happy"
        assert expr1.eyes_layer is None
        
        # 分离模式
        expr2 = ExpressionDefinition(
            id="normal",
            eyes_layer="eyes_normal",
            mouth_layer="mouth_normal",
            eyebrows_layer="brows_normal",
        )
        assert expr2.composite_layer is None
        assert expr2.eyes_layer == "eyes_normal"
    
    def test_character_manifest(self):
        """测试角色清单"""
        from higanvn.packaging.layered_sprite import (
            CharacterSpriteManifest,
            LayerDefinition,
            LayerType,
            PoseDefinition,
            ExpressionDefinition,
            OutfitDefinition,
        )
        
        manifest = CharacterSpriteManifest(
            id="alice",
            name="爱丽丝",
            canvas_width=1024,
            canvas_height=1536,
        )
        
        # 添加底图
        manifest.layers["base_normal"] = LayerDefinition(
            id="base_normal",
            layer_type=LayerType.BASE,
            file="base/normal.png",
            z_order=0,
        )
        
        # 添加表情
        manifest.layers["face_happy"] = LayerDefinition(
            id="face_happy",
            layer_type=LayerType.FACE_COMPOSITE,
            file="face/happy.png",
            z_order=100,
        )
        
        # 添加姿势
        manifest.poses["normal"] = PoseDefinition(
            id="normal",
            base_layer="base_normal",
            face_offset=(256, 100),
        )
        
        # 添加表情定义
        manifest.expressions["happy"] = ExpressionDefinition(
            id="happy",
            composite_layer="face_happy",
        )
        
        # 序列化
        json_str = manifest.to_json()
        data = json.loads(json_str)
        
        assert data['id'] == "alice"
        assert data['name'] == "爱丽丝"
        assert "base_normal" in data['layers']
        
        # 反序列化
        manifest2 = CharacterSpriteManifest.from_json(json_str)
        assert manifest2.id == manifest.id
        assert "base_normal" in manifest2.layers
        assert "normal" in manifest2.poses
    
    def test_sprite_state(self):
        """测试立绘状态"""
        from higanvn.packaging.layered_sprite import SpriteState
        
        state = SpriteState(
            character_id="alice",
            pose="normal",
            expression="happy",
            outfit="school",
        )
        
        key = state.get_cache_key()
        assert "alice" in key
        assert "normal" in key
        assert "happy" in key
    
    def test_sprite_compositor(self):
        """测试立绘合成器"""
        from higanvn.packaging.layered_sprite import (
            CharacterSpriteManifest,
            LayerDefinition,
            LayerType,
            PoseDefinition,
            ExpressionDefinition,
            OutfitDefinition,
            SpriteState,
            SpriteCompositor,
        )
        
        # 创建测试 manifest
        manifest = CharacterSpriteManifest(id="test", name="Test")
        
        # 身体底图
        manifest.layers["base_normal"] = LayerDefinition(
            id="base_normal",
            layer_type=LayerType.BASE,
            file="base/normal.png",
            z_order=0,
        )
        
        # 服装
        manifest.layers["outfit_school"] = LayerDefinition(
            id="outfit_school",
            layer_type=LayerType.OUTFIT,
            file="outfit/school/body.png",
            z_order=50,
        )
        
        # 表情
        manifest.layers["face_happy"] = LayerDefinition(
            id="face_happy",
            layer_type=LayerType.FACE_COMPOSITE,
            file="face/happy.png",
            z_order=100,
        )
        
        # 姿势定义
        manifest.poses["normal"] = PoseDefinition(
            id="normal",
            base_layer="base_normal",
            face_offset=(0, 0),
        )
        
        # 表情定义
        manifest.expressions["happy"] = ExpressionDefinition(
            id="happy",
            composite_layer="face_happy",
        )
        
        # 服装定义
        manifest.outfits["school"] = OutfitDefinition(
            id="school",
            layers=[manifest.layers["outfit_school"]],
        )
        
        # 合成测试
        compositor = SpriteCompositor(manifest)
        state = SpriteState(
            character_id="test",
            pose="normal",
            expression="happy",
            outfit="school",
        )
        
        layers = compositor.get_render_layers(state)
        
        # 应该有 3 层：底图、服装、表情
        assert len(layers) == 3
        
        # 检查顺序（按 z_order 排序）
        z_orders = [l[0].z_order for l in layers]
        assert z_orders == sorted(z_orders)
        
        # 获取所需文件
        files = compositor.get_required_files(state)
        assert "base/normal.png" in files
        assert "outfit/school/body.png" in files
        assert "face/happy.png" in files
    
    def test_create_character_template(self):
        """测试创建角色模板"""
        from higanvn.packaging.layered_sprite import create_character_template
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            manifest = create_character_template(
                character_id="alice",
                name="爱丽丝",
                output_dir=output_dir,
                expressions=['normal', 'happy', 'sad'],
                outfits=['default', 'school'],
                poses=['normal', 'sit'],
            )
            
            # 检查目录结构
            char_dir = output_dir / "alice"
            assert (char_dir / "manifest.json").exists()
            assert (char_dir / "base").exists()
            assert (char_dir / "face").exists()
            assert (char_dir / "outfit" / "default").exists()
            assert (char_dir / "outfit" / "school").exists()
            
            # 检查 manifest 内容
            assert len(manifest.poses) == 2
            assert len(manifest.expressions) == 3
            assert len(manifest.outfits) == 2


class TestPatchArchiveSystem:
    """测试分包加密系统"""
    
    def test_import(self):
        """测试模块导入"""
        from higanvn.packaging.patch_archive import (
            PatchType,
            CompressionType,
            EncryptionType,
            PatchEntry,
            PatchInfo,
            PatchBuilder,
            PatchLoader,
            PatchRegistry,
        )
    
    def test_patch_type_enum(self):
        """测试分包类型枚举"""
        from higanvn.packaging.patch_archive import PatchType
        
        assert PatchType.GRAPHICS.value == "graphics"
        assert PatchType.VOICE.value == "voice"
        assert PatchType.DLC.value == "dlc"
    
    def test_xor_encryption(self):
        """测试 XOR 加密"""
        from higanvn.packaging.patch_archive import xor_encrypt, xor_decrypt
        
        data = b"Hello, World! This is a test message."
        key = b"secret_key_12345"
        
        encrypted = xor_encrypt(data, key)
        assert encrypted != data
        
        decrypted = xor_decrypt(encrypted, key)
        assert decrypted == data
    
    def test_key_derivation(self):
        """测试密钥派生"""
        from higanvn.packaging.patch_archive import derive_key, KEY_SIZE
        
        key1 = derive_key("password123")
        key2 = derive_key("password123")
        key3 = derive_key("different")
        
        assert len(key1) == KEY_SIZE
        assert key1 == key2  # 相同密码应产生相同密钥
        assert key1 != key3  # 不同密码应产生不同密钥
    
    def test_encryption_verification(self):
        """测试加密验证"""
        from higanvn.packaging.patch_archive import (
            derive_key,
            generate_encryption_check,
            verify_encryption_key,
        )
        
        key = derive_key("test_password")
        check = generate_encryption_check(key)
        
        assert verify_encryption_key(key, check)
        
        wrong_key = derive_key("wrong_password")
        assert not verify_encryption_key(wrong_key, check)
    
    def test_patch_entry(self):
        """测试分包条目"""
        from higanvn.packaging.patch_archive import PatchEntry, CompressionType
        
        entry = PatchEntry(
            path="characters/alice/base/normal.png",
            size=102400,
            compressed_size=51200,
            offset=1024,
            hash_md5="abc123def456",
        )
        
        d = entry.to_dict()
        assert d['path'] == "characters/alice/base/normal.png"
        assert d['size'] == 102400
        
        entry2 = PatchEntry.from_dict(d)
        assert entry2.path == entry.path
        assert entry2.compression == CompressionType.ZLIB
    
    def test_patch_info(self):
        """测试分包信息"""
        from higanvn.packaging.patch_archive import PatchInfo, PatchType, PatchEntry
        
        info = PatchInfo(
            name="patch1",
            patch_type=PatchType.GRAPHICS,
            version="1.0.0",
            priority=0,
        )
        
        info.entries["test.png"] = PatchEntry(
            path="test.png",
            size=1000,
            compressed_size=500,
            offset=0,
            hash_md5="test",
        )
        
        json_str = info.to_json()
        info2 = PatchInfo.from_json(json_str)
        
        assert info2.name == "patch1"
        assert info2.patch_type == PatchType.GRAPHICS
        assert "test.png" in info2.entries
    
    def test_patch_builder_and_loader(self):
        """测试分包构建和加载"""
        from higanvn.packaging.patch_archive import (
            PatchBuilder,
            PatchLoader,
            PatchType,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # 创建测试文件
            source_dir = tmpdir / "source"
            source_dir.mkdir()
            
            (source_dir / "file1.txt").write_text("Hello World!")
            (source_dir / "subdir").mkdir()
            (source_dir / "subdir" / "file2.txt").write_text("Test content 123")
            
            # 构建分包
            output_path = tmpdir / "test.hgp"
            builder = PatchBuilder(
                name="test",
                patch_type=PatchType.SCRIPT,
                output_path=output_path,
            )
            builder.add_directory(source_dir)
            info = builder.build(version="1.0.0")
            
            assert output_path.exists()
            assert info.total_files == 2
            
            # 加载分包
            loader = PatchLoader(output_path)
            
            assert loader.exists("file1.txt")
            assert loader.exists("subdir/file2.txt")
            
            content1 = loader.read("file1.txt")
            assert content1 == b"Hello World!"
            
            content2 = loader.read("subdir/file2.txt")
            assert content2 == b"Test content 123"
    
    def test_encrypted_patch(self):
        """测试加密分包"""
        from higanvn.packaging.patch_archive import (
            PatchBuilder,
            PatchLoader,
            PatchType,
            EncryptionType,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # 创建测试文件
            source_file = tmpdir / "secret.txt"
            source_file.write_text("Secret data that should be encrypted")
            
            # 使用密码构建
            output_path = tmpdir / "encrypted.hgp"
            builder = PatchBuilder(
                name="encrypted",
                patch_type=PatchType.SCRIPT,
                output_path=output_path,
                password="my_secret_password",
            )
            builder.add_file(source_file, "secret.txt")
            info = builder.build()
            
            assert info.encryption == EncryptionType.XOR
            assert info.encryption_check != ""
            
            # 正确密码可以读取
            loader = PatchLoader(output_path, password="my_secret_password")
            content = loader.read("secret.txt")
            assert content == b"Secret data that should be encrypted"
            
            # 错误密码应该失败
            with pytest.raises(ValueError, match="Invalid encryption password"):
                PatchLoader(output_path, password="wrong_password")
            
            # 没有密码应该失败
            with pytest.raises(ValueError, match="no password provided"):
                PatchLoader(output_path)
    
    def test_patch_extract(self):
        """测试分包提取"""
        from higanvn.packaging.patch_archive import (
            PatchBuilder,
            PatchLoader,
            PatchType,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # 创建源文件
            source_dir = tmpdir / "source"
            source_dir.mkdir()
            (source_dir / "a.txt").write_text("File A")
            (source_dir / "b.txt").write_text("File B")
            
            # 构建
            output_path = tmpdir / "test.hgp"
            builder = PatchBuilder("test", PatchType.SCRIPT, output_path)
            builder.add_directory(source_dir)
            builder.build()
            
            # 提取
            extract_dir = tmpdir / "extracted"
            loader = PatchLoader(output_path)
            loader.extract_all(extract_dir)
            
            assert (extract_dir / "a.txt").read_text() == "File A"
            assert (extract_dir / "b.txt").read_text() == "File B"
    
    def test_patch_registry(self):
        """测试分包注册表"""
        from higanvn.packaging.patch_archive import (
            PatchBuilder,
            PatchRegistry,
            PatchType,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            
            # 创建多个分包
            for i, (name, ptype) in enumerate([
                ("patch1", PatchType.GRAPHICS),
                ("patch2", PatchType.VOICE),
            ]):
                source = data_dir / f"src_{name}"
                source.mkdir()
                (source / "test.txt").write_text(f"Content from {name}")
                
                builder = PatchBuilder(
                    name=name,
                    patch_type=ptype,
                    output_path=data_dir / f"{name}.hgp",
                )
                builder.add_directory(source)
                builder.info.priority = i
                builder.build()
            
            # 加载注册表
            registry = PatchRegistry(data_dir)
            
            assert len(registry.registry) == 2
            
            # 加载所有分包
            registry.load_all()
            
            # 读取文件
            content = registry.read("test.txt")
            # 高优先级（patch2）应该被返回
            assert content == b"Content from patch2"
            
            registry.close_all()
    
    def test_package_game(self):
        """测试完整游戏打包"""
        from higanvn.packaging.patch_archive import package_game
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            output_dir = Path(tmpdir) / "output"
            
            # 创建项目结构
            (project_dir / "assets" / "characters").mkdir(parents=True)
            (project_dir / "assets" / "characters" / "test.png").write_bytes(b"PNG_DATA")
            
            (project_dir / "assets" / "backgrounds").mkdir(parents=True)
            (project_dir / "assets" / "backgrounds" / "bg.jpg").write_bytes(b"JPG_DATA")
            
            (project_dir / "assets" / "audio" / "bgm").mkdir(parents=True)
            (project_dir / "assets" / "audio" / "bgm" / "theme.ogg").write_bytes(b"OGG_DATA")
            
            (project_dir / "scripts").mkdir(parents=True)
            (project_dir / "scripts" / "main.vns").write_text("*start\n> END")
            
            # 打包
            patches = package_game(project_dir, output_dir, version="1.0.0")
            
            # 验证
            assert (output_dir / "patch1.hgp").exists()  # 图形
            assert (output_dir / "patch3.hgp").exists()  # 音频
            assert (output_dir / "patch4.hgp").exists()  # 脚本
            assert (output_dir / "patches.json").exists()
            
            # 检查注册表
            import json
            with open(output_dir / "patches.json") as f:
                registry = json.load(f)
            assert registry['game_version'] == "1.0.0"
            assert len(registry['patches']) >= 3
