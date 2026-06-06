<template>
  <section class="library-layout">
    <aside class="library-sidebar">
      <div class="library-brand">
        <p class="brand-kicker">Workspace</p>
        <h2>文献库</h2>
      </div>

      <nav class="library-nav">
        <button class="nav-item active">文献库管理</button>
        <button class="nav-item" @click="goAcademicAIWorkspace">学术 AI</button>
        <button class="nav-item" @click="goCitations">引用助手</button>
      </nav>

      <section class="folder-section">
        <div class="folder-head">
          <h3>文件夹</h3>
          <button class="icon-btn" @click="showFolderForm = !showFolderForm">+</button>
        </div>

        <form v-if="showFolderForm" class="folder-form" @submit.prevent="onCreateFolder">
          <input v-model="folderForm.name" placeholder="新建文件夹名称" />
          <button type="submit">创建</button>
        </form>

        <ul class="folder-list">
          <li :class="{ active: selectedFolderId === '' }" @click="selectedFolderId = ''">全部文献</li>
          <li
            v-for="folder in displayFolders"
            :key="folder.id"
            :class="{ active: selectedFolderId === folder.id }"
            @click="selectedFolderId = folder.id"
          >
            <div class="folder-item-row" :style="{ paddingLeft: `${8 + folder._depth * 16}px` }">
              <span class="folder-name">{{ folder.name }}</span>
              <button class="folder-more-btn" @click.stop="toggleFolderMenu(folder.id)">•••</button>
            </div>

            <div v-if="openFolderMenuId === folder.id" class="folder-menu" @click.stop>
              <button @click="startRenameFolder(folder)">重命名</button>
              <button @click="openCreateChildFolder(folder)">创建子文件夹</button>
              <button class="danger" @click="onDeleteFolder(folder)">删除</button>
            </div>

            <div v-if="renamingFolderId === folder.id" class="folder-inline-panel" @click.stop>
              <input v-model="renamingFolderName" placeholder="新的文件夹名称" @keyup.enter="submitRenameFolder(folder.id)" />
              <div class="inline-actions">
                <button @click="submitRenameFolder(folder.id)">保存</button>
                <button class="btn-secondary" @click="cancelRenameFolder">取消</button>
              </div>
            </div>

            <div v-if="creatingChildForFolderId === folder.id" class="folder-inline-panel" @click.stop>
              <input v-model="childFolderName" placeholder="子文件夹名称" @keyup.enter="submitCreateChildFolder(folder.id)" />
              <div class="inline-actions">
                <button @click="submitCreateChildFolder(folder.id)">创建</button>
                <button class="btn-secondary" @click="cancelCreateChildFolder">取消</button>
              </div>
            </div>
          </li>
        </ul>
      </section>
    </aside>

    <section class="library-main">
      <header class="library-header">
        <div>
          <h1>文献库</h1>
          <p>共 {{ papers.length }} 篇</p>
        </div>
        <div class="header-actions">
          <button class="btn-secondary" @click="showPaperForm = !showPaperForm">
            {{ showPaperForm ? "收起表单" : "添加文章" }}
          </button>
          <div class="view-switch">
            <button :class="{ active: viewMode === 'card' }" @click="setViewMode('card')">卡片</button>
            <button :class="{ active: viewMode === 'list' }" @click="setViewMode('list')">列表</button>
          </div>
        </div>
      </header>

      <section class="library-toolbar">
        <div class="search-line">
          <input v-model="searchInput" placeholder="按标题、作者、来源搜索" @keyup.enter="onSearch" />
          <button @click="onSearch">搜索</button>
        </div>
        <div class="sort-line">
          <label for="sortSelect">排序</label>
          <div class="sort-pill">
            <select id="sortSelect" v-model="selectedSort">
              <option value="created_at_desc">添加时间：从新到旧</option>
              <option value="created_at_asc">添加时间：从旧到新</option>
              <option value="last_opened_at_desc">最近阅读：从新到旧</option>
              <option value="last_opened_at_asc">最近阅读：从旧到新</option>
            </select>
            <span class="sort-arrow">▾</span>
          </div>
        </div>
      </section>

      <form v-if="showPaperForm" class="quick-paper-form" @submit.prevent="onCreatePaper">
        <input v-model="paperForm.title" placeholder="论文标题" required />
        <input v-model="paperForm.authors" placeholder="作者" />
        <input v-model="paperForm.conference" placeholder="会议/期刊来源" />
        <button type="submit">保存</button>
      </form>

      <section v-if="showPaperForm" class="upload-panel">
        <div
          class="batch-upload-zone"
          :class="{ dragging: batchDragActive }"
          @click="openBatchPicker"
          @dragenter.prevent="batchDragActive = true"
          @dragover.prevent="batchDragActive = true"
          @dragleave.prevent="batchDragActive = false"
          @drop.prevent="onBatchDrop"
        >
          <input
            ref="batchFileInputRef"
            type="file"
            accept="application/pdf,.pdf"
            multiple
            class="sr-only-input"
            @change="onBatchPicked"
          />
          <strong>导入 PDF</strong>
          <p>点击选择一个或多个 PDF，或将文件拖拽到这里。导入后会自动保存到当前文件夹。</p>
          <button type="button" class="btn-secondary" :disabled="batchUploading" @click.stop="openBatchPicker">
            选择 PDF 文件
          </button>
        </div>

        <div v-if="batchItems.length" class="batch-upload-list">
          <div class="batch-upload-head">
            <strong>待上传文件</strong>
            <div class="batch-upload-actions">
              <button class="btn-secondary" :disabled="batchUploading || !hasBatchPending" @click="uploadAllBatchItems">
                {{ batchUploading ? "上传中..." : "开始上传" }}
              </button>
              <button class="btn-secondary" :disabled="batchUploading" @click="clearBatchItems">清空列表</button>
            </div>
          </div>

          <article
            v-for="item in batchItems"
            :key="item.id"
            :class="['batch-file-row', item.status]"
          >
            <div>
              <strong>{{ item.name }}</strong>
              <span>{{ formatFileSize(item.size) }}</span>
            </div>
            <p>{{ batchStatusText(item) }}</p>
            <button
              v-if="item.status === 'failed'"
              class="btn-secondary"
              :disabled="batchUploading || item.invalid"
              @click="retryBatchItem(item.id)"
            >
              重试
            </button>
          </article>
        </div>
      </section>

      <section v-if="loading" class="card">
        <p>正在加载文献...</p>
      </section>

      <section v-else-if="viewMode === 'card'" class="paper-card-grid">
        <article v-for="paper in papers" :key="paper.id" class="paper-card-item" @click="goReader(paper.id)">
          <div class="paper-card-head">
            <div class="paper-head-left">📖 {{ paper.page_progress || "1/23" }}</div>
            <div class="paper-head-right">
              <button class="ai-pill" @click.stop="goAcademicAI(paper.id)">AI 速读</button>
              <button class="read-pill" @click.stop="goReader(paper.id)">速览</button>
              <button class="more-pill" @click.stop="togglePaperMenu(paper.id, 'card')">•••</button>
            </div>

            <div class="paper-preview-box">
              <img
                v-if="paperPreviewById[paper.id]"
                class="paper-preview-image"
                :src="paperPreviewById[paper.id]"
                :alt="`${paper.title} 首页预览`"
              />
              <div v-else class="paper-preview-page"></div>
            </div>
            <div class="paper-year-side">{{ paper.year || "2025" }}</div>
          </div>

          <div class="paper-card-body">
            <h3>{{ paper.title }}</h3>
            <p class="paper-authors">作者：{{ paper.authors || "未知" }}</p>
            <p class="paper-source">来源：{{ paper.conference || "未填写" }}</p>
            <p class="paper-source">引用信息：{{ hasCitationMetadata(paper) ? "已识别" : "待补全" }}</p>
            <p class="paper-source">分组：{{ getFolderNameById(paper.folder_id) }}</p>
          </div>

          <div
            v-if="openPaperMenuId === paper.id && paperMenuAnchor === 'card'"
            class="card-more-menu"
            @click.stop
          >
            <button @click="showPaperInfo(paper)">信息</button>
            <button @click="onExtractCitationMetadata(paper)">补全引用信息</button>
            <button @click="openMovePopover(paper.id, 'card')">移动至文件夹</button>
            <button @click="onEditPaper(paper)">编辑</button>
            <button class="danger" @click="onDeletePaper(paper.id)">删除</button>
          </div>

          <div
            v-if="movePopoverPaperId === paper.id && movePopoverAnchor === 'card'"
            class="move-folder-popover"
            @click.stop
          >
            <input v-model="moveSearchKeyword" placeholder="搜索或创建文件夹" />

            <div class="move-folder-list">
              <button class="folder-choice" :class="{ active: targetFolderByPaper[paper.id] === '' }" @click="targetFolderByPaper[paper.id] = ''">
                <span class="folder-dot"></span>
                <span>未分组</span>
              </button>
              <button
                v-for="folder in getFilteredFolders()"
                :key="folder.id"
                class="folder-choice"
                :class="{ active: targetFolderByPaper[paper.id] === folder.id }"
                @click="targetFolderByPaper[paper.id] = folder.id"
              >
                <span class="folder-dot"></span>
                <span>{{ folder.name }}</span>
              </button>
            </div>

            <div class="move-folder-actions">
              <button @click="confirmMoveToFolder(paper.id)">移动到所选</button>
            </div>
            <div class="move-create-row">
              <input v-model="newFolderByPaper[paper.id]" placeholder="新建文件夹名称" />
              <button class="btn-secondary" @click="onCreateFolderAndAssign(paper.id)">新建并移动</button>
            </div>
          </div>
        </article>
      </section>

      <section v-else class="paper-list-wrap">
        <table>
          <thead>
            <tr>
              <th>标题</th>
              <th>作者</th>
              <th>来源</th>
              <th>分组</th>
              <th>添加时间</th>
              <th>最近阅读</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="paper in papers" :key="paper.id">
              <td>{{ paper.title }}</td>
              <td>{{ paper.authors || "-" }}</td>
              <td>{{ paper.conference || "-" }}</td>
              <td>{{ getFolderNameById(paper.folder_id) }}</td>
              <td>{{ formatDate(paper.created_at) }}</td>
              <td>{{ formatDate(paper.last_opened_at) }}</td>
              <td class="ops-cell">
                <div class="list-op-row">
                  <button @click="goReader(paper.id)">打开</button>
                  <button class="btn-secondary" @click="goAcademicAI(paper.id)">AI 速读</button>
                  <button class="more-pill list-more-btn" @click.stop="togglePaperMenu(paper.id, 'list')">•••</button>
                </div>

                <div
                  v-if="openPaperMenuId === paper.id && paperMenuAnchor === 'list'"
                  class="list-more-menu"
                  @click.stop
                >
                  <button @click="showPaperInfo(paper)">信息</button>
                  <button @click="onExtractCitationMetadata(paper)">补全引用信息</button>
                  <button @click="openMovePopover(paper.id, 'list')">移动至文件夹</button>
                  <button @click="onEditPaper(paper)">编辑</button>
                  <button class="danger" @click="onDeletePaper(paper.id)">删除</button>
                </div>

                <div
                  v-if="movePopoverPaperId === paper.id && movePopoverAnchor === 'list'"
                  class="list-move-popover"
                  @click.stop
                >
                  <input v-model="moveSearchKeyword" placeholder="搜索或创建文件夹" />
                  <div class="move-folder-list">
                    <button class="folder-choice" :class="{ active: targetFolderByPaper[paper.id] === '' }" @click="targetFolderByPaper[paper.id] = ''">
                      <span class="folder-dot"></span>
                      <span>未分组</span>
                    </button>
                    <button
                      v-for="folder in getFilteredFolders()"
                      :key="folder.id"
                      class="folder-choice"
                      :class="{ active: targetFolderByPaper[paper.id] === folder.id }"
                      @click="targetFolderByPaper[paper.id] = folder.id"
                    >
                      <span class="folder-dot"></span>
                      <span>{{ folder.name }}</span>
                    </button>
                  </div>
                  <div class="move-folder-actions">
                    <button @click="confirmMoveToFolder(paper.id)">移动到所选</button>
                  </div>
                  <div class="move-create-row">
                    <input v-model="newFolderByPaper[paper.id]" placeholder="新建文件夹名称" />
                    <button class="btn-secondary" @click="onCreateFolderAndAssign(paper.id)">新建并移动</button>
                  </div>
                </div>
              </td>
            </tr>
            <tr v-if="papers.length === 0">
              <td colspan="7">暂无文献</td>
            </tr>
          </tbody>
        </table>
      </section>
    </section>

    <div v-if="modal.open" class="app-modal-backdrop" @click.self="closeModal">
      <section v-if="modal.type === 'confirm'" class="app-modal app-modal-sm">
        <header class="app-modal-header">
          <h3>{{ modal.title }}</h3>
          <button class="modal-close" @click="closeModal">×</button>
        </header>
        <div class="app-modal-body">
          <p>{{ modal.message }}</p>
        </div>
        <footer class="app-modal-footer">
          <button class="btn-secondary" @click="closeModal">取消</button>
          <button @click="confirmModalAction">确定</button>
        </footer>
      </section>

      <section v-else-if="modal.type === 'notice'" class="app-modal app-modal-sm">
        <header class="app-modal-header">
          <h3>{{ modal.title }}</h3>
          <button class="modal-close" @click="closeModal">×</button>
        </header>
        <div class="app-modal-body">
          <p>{{ modal.message }}</p>
        </div>
        <footer class="app-modal-footer">
          <button @click="closeModal">我知道了</button>
        </footer>
      </section>

      <section v-else-if="modal.type === 'editPaper'" class="app-modal app-modal-md">
        <header class="app-modal-header">
          <h3>编辑文献</h3>
          <button class="modal-close" @click="closeModal">×</button>
        </header>
        <div class="app-modal-body form-stack">
          <label>
            标题
            <input v-model="editPaperForm.title" placeholder="请输入标题" />
          </label>
          <label>
            作者
            <input v-model="editPaperForm.authors" placeholder="请输入作者" />
          </label>
          <label>
            来源
            <input v-model="editPaperForm.conference" placeholder="请输入来源" />
          </label>
        </div>
        <footer class="app-modal-footer">
          <button class="btn-secondary" @click="closeModal">取消</button>
          <button @click="submitEditPaper">保存修改</button>
        </footer>
      </section>

      <section v-else-if="modal.type === 'paperInfo'" class="app-modal app-modal-lg">
        <header class="app-modal-header">
          <h3>信息</h3>
          <button class="modal-close" @click="closeModal">×</button>
        </header>
        <div class="app-modal-body paper-info-body">
          <div class="paper-info-cover">
            <div class="mini-paper-preview">
              <img
                v-if="paperPreviewById[infoPaper.id]"
                class="mini-paper-preview-image"
                :src="paperPreviewById[infoPaper.id]"
                :alt="`${infoPaper.title} 首页预览`"
              />
            </div>
          </div>
          <div class="paper-info-main">
            <div class="paper-info-row"><strong>标题：</strong><span>{{ infoPaper.title }}</span></div>
            <div class="paper-info-row"><strong>作者：</strong><span>{{ infoPaper.authors || "-" }}</span></div>
            <div class="paper-info-row"><strong>来源：</strong><span>{{ infoPaper.conference || "-" }}</span></div>
            <div class="paper-info-row"><strong>分组：</strong><span>{{ getFolderNameById(infoPaper.folder_id) }}</span></div>
            <div class="paper-info-row"><strong>添加日期：</strong><span>{{ formatDate(infoPaper.created_at) }}</span></div>
            <div class="paper-info-row"><strong>上次阅读：</strong><span>{{ formatDate(infoPaper.last_opened_at) }}</span></div>
          </div>
        </div>
        <footer class="app-modal-footer">
          <button @click="closeModal">关闭</button>
        </footer>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { GlobalWorkerOptions, getDocument } from "pdfjs-dist";
import pdfWorkerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";

import {
  createFolder,
  createPaper,
  deleteFolder,
  deletePaper,
  extractPaperCitationMetadata,
  fetchFolders,
  fetchPapers,
  updateFolder,
  updatePaper,
  uploadPaperPdf
} from "@/services/api";

GlobalWorkerOptions.workerSrc = pdfWorkerSrc;

const router = useRouter();

const folders = ref([]);
const papers = ref([]);
const paperPreviewById = ref({});
const selectedFolderId = ref("");
const searchInput = ref("");
const searchKeyword = ref("");
const loading = ref(false);
const showFolderForm = ref(false);
const showPaperForm = ref(false);
const viewMode = ref(localStorage.getItem("paper_reader_view_mode") || "card");
const selectedSort = ref(localStorage.getItem("paper_reader_sort") || "last_opened_at_desc");

const targetFolderByPaper = ref({});
const newFolderByPaper = ref({});

const openPaperMenuId = ref("");
const paperMenuAnchor = ref("card");
const movePopoverPaperId = ref("");
const movePopoverAnchor = ref("card");
const moveSearchKeyword = ref("");

const openFolderMenuId = ref("");
const renamingFolderId = ref("");
const renamingFolderName = ref("");
const creatingChildForFolderId = ref("");
const childFolderName = ref("");

const batchFileInputRef = ref(null);
const batchItems = ref([]);
const batchUploading = ref(false);
const batchDragActive = ref(false);
const citationParsingId = ref("");

const modal = reactive({
  open: false,
  type: "",
  title: "",
  message: "",
  action: "",
  payload: null
});

const editPaperForm = reactive({
  id: "",
  title: "",
  authors: "",
  conference: ""
});

const infoPaper = reactive({
  id: "",
  title: "",
  authors: "",
  conference: "",
  file_url: "",
  folder_id: "",
  created_at: "",
  last_opened_at: ""
});

const folderForm = reactive({ name: "" });
const paperForm = reactive({
  title: "",
  authors: "",
  conference: ""
});
const hasBatchPending = computed(() => batchItems.value.some((item) => item.status === "waiting" || item.status === "failed"));
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api/v1";
const backendOrigin = new URL(apiBaseUrl, window.location.origin).origin;
const pdfPreviewCacheByUrl = new Map();
const pdfPreviewPendingByUrl = new Map();

function toAbsoluteUploadUrl(url) {
  if (!url) return "";
  if (/^https?:\/\//i.test(url)) return url;
  return url.startsWith("/") ? `${backendOrigin}${url}` : `${backendOrigin}/${url}`;
}

const displayFolders = computed(() => {
  const byParent = new Map();
  for (const folder of folders.value) {
    const parent = folder.parent_id || "";
    if (!byParent.has(parent)) byParent.set(parent, []);
    byParent.get(parent).push(folder);
  }

  for (const list of byParent.values()) {
    list.sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), "zh-CN"));
  }

  const visited = new Set();
  const out = [];

  function walk(parentId, depth) {
    const list = byParent.get(parentId) || [];
    for (const item of list) {
      if (visited.has(item.id)) continue;
      visited.add(item.id);
      out.push({ ...item, _depth: depth });
      walk(item.id, depth + 1);
    }
  }

  walk("", 0);
  for (const folder of folders.value) {
    if (!visited.has(folder.id)) {
      out.push({ ...folder, _depth: 0 });
    }
  }
  return out;
});

function parseSortValue(value) {
  if (value.endsWith("_asc")) return { sort_by: value.slice(0, -4), sort_order: "asc" };
  if (value.endsWith("_desc")) return { sort_by: value.slice(0, -5), sort_order: "desc" };
  return { sort_by: "last_opened_at", sort_order: "desc" };
}

async function loadFolders() {
  folders.value = await fetchFolders();
}

async function loadPapers() {
  loading.value = true;
  try {
    const params = {};
    if (selectedFolderId.value) params.folder_id = selectedFolderId.value;
    if (searchKeyword.value) params.q = searchKeyword.value;
    const sortParams = parseSortValue(selectedSort.value);
    params.sort_by = sortParams.sort_by;
    params.sort_order = sortParams.sort_order;

    papers.value = await fetchPapers(params);

    const targetMap = {};
    const newMap = {};
    for (const paper of papers.value) {
      targetMap[paper.id] = paper.folder_id || "";
      newMap[paper.id] = "";
    }
    targetFolderByPaper.value = targetMap;
    newFolderByPaper.value = newMap;
    hydratePaperPreviews(papers.value);
  } finally {
    loading.value = false;
  }
}

function hydratePaperPreviews(list) {
  for (const paper of list || []) {
    void ensurePaperPreview(paper);
  }
}

async function ensurePaperPreview(paper) {
  const paperId = String(paper?.id || "").trim();
  const fileUrl = toAbsoluteUploadUrl(String(paper?.file_url || "").trim());
  if (!paperId || !fileUrl) return;
  if (paperPreviewById.value[paperId]) return;

  const previewDataUrl = await getPdfFirstPagePreview(fileUrl);
  if (!previewDataUrl) return;
  paperPreviewById.value = { ...paperPreviewById.value, [paperId]: previewDataUrl };
}

async function getPdfFirstPagePreview(fileUrl) {
  if (!fileUrl) return "";
  if (pdfPreviewCacheByUrl.has(fileUrl)) {
    return pdfPreviewCacheByUrl.get(fileUrl);
  }
  if (pdfPreviewPendingByUrl.has(fileUrl)) {
    return pdfPreviewPendingByUrl.get(fileUrl);
  }

  const pending = (async () => {
    let pdfDoc = null;
    try {
      const loadingTask = getDocument({ url: fileUrl, withCredentials: true });
      pdfDoc = await loadingTask.promise;
      const firstPage = await pdfDoc.getPage(1);
      const viewport = firstPage.getViewport({ scale: 1 });
      const targetWidth = 460;
      const scale = Math.max(targetWidth / viewport.width, 1);
      const scaledViewport = firstPage.getViewport({ scale });

      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d", { alpha: false });
      if (!context) return "";

      canvas.width = Math.floor(scaledViewport.width);
      canvas.height = Math.floor(scaledViewport.height);

      await firstPage.render({
        canvasContext: context,
        viewport: scaledViewport
      }).promise;

      const previewDataUrl = canvas.toDataURL("image/jpeg", 0.86);
      pdfPreviewCacheByUrl.set(fileUrl, previewDataUrl);
      return previewDataUrl;
    } catch {
      return "";
    } finally {
      pdfPreviewPendingByUrl.delete(fileUrl);
      if (pdfDoc) {
        await pdfDoc.destroy();
      }
    }
  })();

  pdfPreviewPendingByUrl.set(fileUrl, pending);
  return pending;
}

function onSearch() {
  searchKeyword.value = searchInput.value.trim();
  loadPapers();
}

function setViewMode(mode) {
  viewMode.value = mode;
  localStorage.setItem("paper_reader_view_mode", mode);
}

async function onCreateFolder() {
  if (!folderForm.name.trim()) return;
  await createFolder({ name: folderForm.name.trim() });
  folderForm.name = "";
  showFolderForm.value = false;
  await loadFolders();
}

function toggleFolderMenu(folderId) {
  openFolderMenuId.value = openFolderMenuId.value === folderId ? "" : folderId;
  renamingFolderId.value = "";
  creatingChildForFolderId.value = "";
}

function startRenameFolder(folder) {
  openFolderMenuId.value = "";
  creatingChildForFolderId.value = "";
  renamingFolderId.value = folder.id;
  renamingFolderName.value = folder.name || "";
}

function cancelRenameFolder() {
  renamingFolderId.value = "";
  renamingFolderName.value = "";
}

async function submitRenameFolder(folderId) {
  const name = renamingFolderName.value.trim();
  if (!name) return;
  await updateFolder(folderId, { name });
  cancelRenameFolder();
  await loadFolders();
}

function openCreateChildFolder(folder) {
  openFolderMenuId.value = "";
  renamingFolderId.value = "";
  creatingChildForFolderId.value = folder.id;
  childFolderName.value = "";
}

function cancelCreateChildFolder() {
  creatingChildForFolderId.value = "";
  childFolderName.value = "";
}

async function submitCreateChildFolder(parentId) {
  const name = childFolderName.value.trim();
  if (!name) return;
  await createFolder({ name, parent_id: parentId });
  cancelCreateChildFolder();
  await loadFolders();
}

async function onDeleteFolder(folder) {
  openFolderMenuId.value = "";
  modal.open = true;
  modal.type = "confirm";
  modal.title = "删除文件夹";
  modal.message = `确认删除文件夹「${folder.name}」吗？子文件夹会保留，文献会变为未分组。`;
  modal.action = "deleteFolder";
  modal.payload = folder;
}

function openBatchPicker() {
  if (batchUploading.value) return;
  batchFileInputRef.value?.click();
}

function isPdfFile(file) {
  const name = String(file?.name || "").toLowerCase();
  return name.endsWith(".pdf") || file?.type === "application/pdf";
}

function createBatchItem(file) {
  const invalidReason = !file
    ? "文件为空"
    : !isPdfFile(file)
      ? "仅支持 PDF 文件"
      : file.size <= 0
        ? "文件为空"
        : "";

  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    file,
    name: file?.name || "未命名文件",
    size: file?.size || 0,
    status: invalidReason ? "failed" : "waiting",
    error: invalidReason,
    invalid: Boolean(invalidReason)
  };
}

function addBatchFiles(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) return;
  const existingKeys = new Set(batchItems.value.map((item) => `${item.name}-${item.size}-${item.file?.lastModified || 0}`));
  const nextItems = [];
  for (const file of files) {
    const key = `${file.name}-${file.size}-${file.lastModified || 0}`;
    if (existingKeys.has(key)) continue;
    existingKeys.add(key);
    nextItems.push(createBatchItem(file));
  }
  batchItems.value = [...batchItems.value, ...nextItems];
}

function onBatchPicked(event) {
  addBatchFiles(event.target.files);
  event.target.value = "";
}

function onBatchDrop(event) {
  batchDragActive.value = false;
  if (batchUploading.value) return;
  addBatchFiles(event.dataTransfer?.files);
}

function clearBatchItems() {
  batchItems.value = [];
}

function formatFileSize(size) {
  if (!size) return "0 KB";
  const mb = size / 1024 / 1024;
  if (mb >= 1) return `${mb.toFixed(2)} MB`;
  return `${Math.max(1, Math.round(size / 1024))} KB`;
}

function batchStatusText(item) {
  if (item.status === "waiting") return "等待上传";
  if (item.status === "uploading") return "上传中...";
  if (item.status === "success") return "上传成功";
  return `上传失败：${item.error || "服务器返回错误"}`;
}

function metadataAuthorsText(metadata) {
  const authors = metadata?.authors;
  if (Array.isArray(authors)) return authors.join(", ");
  return authors || "";
}

function titleFromUploadResult(result, item) {
  const metadata = result?.citation_metadata || result?.citationMetadata || {};
  const title = String(metadata.title || "").trim();
  if (title) return title;
  return String(item.name || "Untitled").replace(/\.pdf$/i, "").trim() || "Untitled";
}

function errorMessageFromUpload(error) {
  if (error?.response?.status === 401) return "登录已失效，请重新登录";
  return error?.response?.data?.error || "服务器返回错误";
}

async function uploadBatchItem(item) {
  if (!item || item.invalid || item.status === "uploading") return false;
  item.status = "uploading";
  item.error = "";
  try {
    const result = await uploadPaperPdf(item.file);
    const metadata = result.citation_metadata || result.citationMetadata || {};
    await createPaper({
      title: titleFromUploadResult(result, item),
      authors: metadataAuthorsText(metadata),
      conference: metadata.venue || metadata.conference || "",
      year: metadata.year,
      file_url: result.relative_url || result.file_url,
      citationMetadata: metadata,
      folder_id: selectedFolderId.value || null
    });
    item.status = "success";
    return true;
  } catch (error) {
    item.status = "failed";
    item.error = errorMessageFromUpload(error);
    return false;
  }
}

async function uploadAllBatchItems() {
  if (batchUploading.value) return;
  const targets = batchItems.value.filter((item) => (item.status === "waiting" || item.status === "failed") && !item.invalid);
  if (!targets.length) return;
  batchUploading.value = true;
  try {
    for (const item of targets) {
      await uploadBatchItem(item);
    }
    await loadPapers();
  } finally {
    batchUploading.value = false;
  }
}

async function retryBatchItem(itemId) {
  if (batchUploading.value) return;
  const item = batchItems.value.find((entry) => entry.id === itemId);
  if (!item || item.invalid) return;
  batchUploading.value = true;
  try {
    await uploadBatchItem(item);
    await loadPapers();
  } finally {
    batchUploading.value = false;
  }
}

async function onCreatePaper() {
  await createPaper({
    ...paperForm,
    file_url: "",
    citationMetadata: {},
    folder_id: selectedFolderId.value || null
  });

  paperForm.title = "";
  paperForm.authors = "";
  paperForm.conference = "";
  showPaperForm.value = false;

  await loadPapers();
}

function getFolderNameById(folderId) {
  if (!folderId) return "未分组";
  const folder = folders.value.find((item) => item.id === folderId);
  return folder ? folder.name : "未分组";
}

function hasCitationMetadata(paper) {
  const metadata = paper?.citationMetadata || {};
  return Boolean(
    metadata.title ||
      metadata.authors?.length ||
      metadata.year ||
      metadata.venue ||
      metadata.doi ||
      metadata.arxivId ||
      metadata.citationText
  );
}

function getFilteredFolders() {
  const keyword = moveSearchKeyword.value.trim().toLowerCase();
  if (!keyword) return folders.value;
  return folders.value.filter((folder) => String(folder.name || "").toLowerCase().includes(keyword));
}

function togglePaperMenu(paperId, anchor = "card") {
  if (openPaperMenuId.value === paperId && paperMenuAnchor.value === anchor) {
    openPaperMenuId.value = "";
    return;
  }
  openPaperMenuId.value = paperId;
  paperMenuAnchor.value = anchor;
  movePopoverPaperId.value = "";
}

function openMovePopover(paperId, anchor = "card") {
  openPaperMenuId.value = "";
  movePopoverPaperId.value = paperId;
  movePopoverAnchor.value = anchor;
  moveSearchKeyword.value = "";
}

async function confirmMoveToFolder(paperId) {
  const folderId = targetFolderByPaper.value[paperId] || null;
  await updatePaper(paperId, { folder_id: folderId });
  movePopoverPaperId.value = "";
  await loadPapers();
}

async function onCreateFolderAndAssign(paperId) {
  const name = (newFolderByPaper.value[paperId] || "").trim();
  if (!name) return;
  const created = await createFolder({ name });
  await updatePaper(paperId, { folder_id: created.id });
  newFolderByPaper.value[paperId] = "";
  movePopoverPaperId.value = "";
  await Promise.all([loadFolders(), loadPapers()]);
}

function showPaperInfo(paper) {
  openPaperMenuId.value = "";
  Object.assign(infoPaper, {
    id: paper.id || "",
    title: paper.title || "",
    authors: paper.authors || "",
    conference: paper.conference || "",
    file_url: paper.file_url || "",
    folder_id: paper.folder_id || "",
    created_at: paper.created_at || "",
    last_opened_at: paper.last_opened_at || ""
  });
  void ensurePaperPreview(paper);
  modal.open = true;
  modal.type = "paperInfo";
  modal.title = "信息";
  modal.message = "";
  modal.action = "";
  modal.payload = null;
}

async function onEditPaper(paper) {
  openPaperMenuId.value = "";
  Object.assign(editPaperForm, {
    id: paper.id || "",
    title: paper.title || "",
    authors: paper.authors || "",
    conference: paper.conference || ""
  });
  modal.open = true;
  modal.type = "editPaper";
  modal.title = "编辑文献";
  modal.message = "";
  modal.action = "";
  modal.payload = null;
}

async function onDeletePaper(paperId) {
  openPaperMenuId.value = "";
  movePopoverPaperId.value = "";
  modal.open = true;
  modal.type = "confirm";
  modal.title = "删除文献";
  modal.message = "确认删除这篇文献吗？删除后不可恢复。";
  modal.action = "deletePaper";
  modal.payload = paperId;
}

async function onExtractCitationMetadata(paper) {
  if (!paper?.id || citationParsingId.value) return;
  openPaperMenuId.value = "";
  citationParsingId.value = paper.id;
  try {
    await extractPaperCitationMetadata(paper.id);
    await loadPapers();
    modal.open = true;
    modal.type = "notice";
    modal.title = "引用信息已补全";
    modal.message = "系统已从 PDF 前几页尝试识别标题、作者、年份、来源、DOI 或 arXiv 信息。";
  } catch (error) {
    modal.open = true;
    modal.type = "notice";
    modal.title = "补全失败";
    modal.message = error?.response?.data?.error || "无法解析该 PDF 的引用信息，请稍后重试或手动编辑。";
  } finally {
    citationParsingId.value = "";
  }
}

function closeModal() {
  modal.open = false;
  modal.type = "";
  modal.title = "";
  modal.message = "";
  modal.action = "";
  modal.payload = null;
}

async function confirmModalAction() {
  if (modal.action === "deleteFolder" && modal.payload) {
    const folder = modal.payload;
    await deleteFolder(folder.id);

    if (selectedFolderId.value === folder.id) {
      selectedFolderId.value = "";
    }
    if (renamingFolderId.value === folder.id) cancelRenameFolder();
    if (creatingChildForFolderId.value === folder.id) cancelCreateChildFolder();

    await Promise.all([loadFolders(), loadPapers()]);
  }

  if (modal.action === "deletePaper" && modal.payload) {
    await deletePaper(modal.payload);
    await loadPapers();
  }

  closeModal();
}

async function submitEditPaper() {
  const title = (editPaperForm.title || "").trim();
  if (!title) {
    modal.type = "notice";
    modal.title = "提示";
    modal.message = "标题不能为空。";
    modal.action = "";
    modal.payload = null;
    return;
  }

  await updatePaper(editPaperForm.id, {
    title,
    authors: (editPaperForm.authors || "").trim(),
    conference: (editPaperForm.conference || "").trim()
  });
  closeModal();
  await loadPapers();
}

function goReader(id) {
  router.push({ name: "reader", params: { id } });
}

function goAcademicAI(id) {
  router.push({ name: "academic-ai", query: { paper_id: id, task: "paper_summary" } });
}

function goAcademicAIWorkspace() {
  router.push({ name: "academic-ai" });
}

function goCitations() {
  router.push({ name: "citations" });
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function handleDocumentClick() {
  openFolderMenuId.value = "";
  openPaperMenuId.value = "";
  movePopoverPaperId.value = "";
}

watch(selectedFolderId, loadPapers);
watch(selectedSort, async (value) => {
  localStorage.setItem("paper_reader_sort", value);
  await loadPapers();
});

onMounted(async () => {
  document.addEventListener("click", handleDocumentClick);
  await Promise.all([loadFolders(), loadPapers()]);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick);
});
</script>
