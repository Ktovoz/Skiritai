# pip → uv 改造方案

## 一、对终端用户的影响：零

**用户仍然可以 `pip install skiritai`**，完全不受影响。

PyPI 上发布的是标准的 `.whl` / `.tar.gz`，用 uv 构建的包和用 pip 构建的包是同一个东西。uv 只是开发/CI 工具链的升级，不改变包的发布格式。

---

## 二、改造范围总览

| 文件 | 改动 |
|------|------|
| `pyproject.toml` | build-backend 改为 `hatchling`，删除 setuptools 配置，补充 hatchling 等价配置 |
| `.github/workflows/test.yml` | `pip install` → `uv pip install`，pip cache → uv cache，增加 `setup-uv` 步骤 |
| `.github/workflows/publish.yml` | `pip install build twine` → `uv build`，用 `uv` 替代 `python -m build` |
| 新增 `uv.lock` | 由 `uv lock` 自动生成的版本锁文件（提交到 git） |
| 可选 `.python-version` | 固定 Python 版本，方便 `uv` 自动管理 |
| `README.md` / `CONTRIBUTING.md` | 开发者文档：安装指令从 `pip install -e .` 改为 `uv sync` |

---

## 三、逐文件改动详情

### 3.1 `pyproject.toml`

#### build-system 改动

```diff
 [build-system]
-requires = ["setuptools>=68.0", "wheel"]
-build-backend = "setuptools.build_meta"
+requires = ["hatchling"]
+build-backend = "hatchling.build"
```

#### 删除 setuptools 专属配置

```diff
-[tool.setuptools.packages.find]
-include = ["skiritai*"]
-
-[tool.setuptools.package-data]
-skiritai = ["py.typed"]
```

#### 新增 hatchling 等价配置

Hatchling 默认会自动发现 `skiritai` 包，且默认包含 `py.typed`，无需额外配置。

但如果需要显式指定（保险起见）：

```toml
[tool.hatch.build.targets.wheel]
packages = ["skiritai"]
```

> **注意**：如果 `skiritai/` 目录下有非 Python 文件需要打包（如 `py.typed`），hatchling 会自动包含 `py.typed`（PEP 561 标准），无需配置。

#### 可选：新增 uv 专属配置

```toml
[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
    "pytest-cov",
]
```

> uv 支持将 dev deps 从 `[project.optional-dependencies]` 中拆分到 `[tool.uv.dev-dependencies]`，这样 `uv sync` 默认安装 dev deps，`uv sync --no-dev` 跳过。

---

### 3.2 `.github/workflows/test.yml`

#### 改动要点

1. 所有 job 增加 `setup-uv` 步骤（或者安装 uv）
2. `pip install -e ".[dev]"` → `uv pip install --system -e ".[dev]"`
3. Cache 路径从 `~/.cache/pip` → uv 的缓存路径
4. `python -m pytest` → 可改为 `uv run pytest`（更简洁）

#### 示例 diff（unit job）

```diff
  unit:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12"]
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

+     - name: Install uv
+       uses: astral-sh/setup-uv@v5
+       with:
+         enable-cache: true
+         cache-dependency-glob: "pyproject.toml"

-     - name: Cache pip packages
-       uses: actions/cache@v4
-       with:
-         path: ~/.cache/pip
-         key: ${{ runner.os }}-pip-${{ matrix.python-version }}-${{ hashFiles('pyproject.toml') }}
-         restore-keys: |
-           ${{ runner.os }}-pip-${{ matrix.python-version }}-

      - name: Install package with dev deps
        run: |
-         pip install -e ".[dev]"
+         uv pip install --system -e ".[dev]"
```

> 说明：
> - `astral-sh/setup-uv@v5` 是 uv 官方 GitHub Action，自带缓存，不需要手写 `actions/cache`。
> - `--system` 是因为 CI 环境不用虚拟环境，直接装到系统 Python 中。
> - `uv pip install` 接口兼容 pip，所以 `-e ".[dev]"` 语法完全一样。

---

### 3.3 `.github/workflows/publish.yml`

#### 改动要点

1. `pip install build twine` → 直接用 `uv build`（不需要安装 build 包）
2. `python -m build` → `uv build`
3. `twine check` → `uv publish --check-url testpypi` 或不使用 twine（uv 内置校验）

#### build job 改动

```diff
  build:
    needs: [validate, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

+     - name: Install uv
+       uses: astral-sh/setup-uv@v5

-     - name: Install build tools
-       run: pip install build twine
+     - name: Build package
+       run: uv build

-     - name: Build package
-       run: python -m build

      - name: Check package
-       run: twine check dist/*
+       run: uvx twine check dist/*

      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
```

> 说明：
> - `uv build` 是内置命令，替代 `python -m build`，不需要安装 build 包。
> - `uvx twine check` 用 uv 的临时环境运行 twine，不需要提前安装。
> - 如果想彻底去掉 twine，`uv publish` 自带 dry-run 校验：`uv publish --check-url https://test.pypi.org/legacy/ --dry-run`。

#### publish-pypi job

```diff
  publish-pypi:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - name: Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

-     - name: Publish to PyPI
-       uses: pypa/gh-action-pypi-publish@release/v1
-       with:
-         password: ${{ secrets.PYPI_API_TOKEN }}
+     - name: Install uv
+       uses: astral-sh/setup-uv@v5
+
+     - name: Publish to PyPI
+       run: uv publish --token ${{ secrets.PYPI_API_TOKEN }}
```

> 说明：`uv publish` 可以替代 `gh-action-pypi-publish`，同样支持 token 认证和 Trusted Publishing。

---

### 3.4 新增 `uv.lock`

运行 `uv lock` 自动生成。需要提交到 git，确保开发者和 CI 使用完全相同的依赖版本。

```
uv lock
git add uv.lock
```

---

### 3.5 可选：`.python-version`

新建文件，内容：

```
3.12
```

uv 会读取这个文件，自动使用指定版本的 Python（如果你还用了 `uv python` 管理 Python 版本的话）。CI 中 `setup-uv` 也可以利用这个文件。

---

## 四、开发者工作流变化

| 操作 | pip 时代 | uv 时代 |
|------|---------|--------|
| 创建环境 + 安装依赖 | `python -m venv .venv && pip install -e ".[dev]"` | `uv sync` |
| 运行测试 | `pytest` | `uv run pytest` |
| 运行 CLI | `skiritai ...` (需手动激活 venv) | `uv run skiritai ...` |
| 构建包 | `python -m build` | `uv build` |
| 发布 | `twine upload dist/*` | `uv publish` |
| 添加依赖 | `pip install xxx` + 手动更新 pyproject.toml | `uv add xxx` |

**核心优势**：
- `uv sync` 一步搞定（比 pip 快 10-100x）
- `uv run` 自动激活 venv，不用手动 `source .venv/bin/activate`
- `uv add` / `uv remove` 自动更新 pyproject.toml 和 uv.lock
- CI 构建速度显著提升（安装依赖从 30s+ 降到 2-5s）

---

## 五、执行步骤（按顺序）

1. **本地安装 uv** — `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. **修改 `pyproject.toml`** — 切换 build-backend 到 hatchling
3. **生成 `uv.lock`** — `uv lock`
4. **验证本地开发流程** — `uv sync && uv run pytest`
5. **验证构建** — `uv build && uvx twine check dist/*`
6. **修改 CI workflows** — test.yml + publish.yml
7. **推分支、跑 CI 验证**
8. **更新 README/贡献指南** — 开发者安装指令
9. **合并到 main**

---

## 六、风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| hatchling 包发现行为与 setuptools 不同 | 低 | 打包缺少文件 | `uv build && tar tzf dist/*.tar.gz` 验证 |
| CI cache 未命中导致首次构建变慢 | 中 | 首次 CI 慢几秒 | `setup-uv` action 自带缓存 |
| `uv publish` token 认证方式不同 | 低 | 发布失败 | 保留降级方案：仍可用 `gh-action-pypi-publish` |
| 团队成员未安装 uv | 中 | 无法本地开发 | 保留 `pip install -e ".[dev]"` 作为降级方案 |
