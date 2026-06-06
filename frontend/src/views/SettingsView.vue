<template>
  <section class="settings-hub">
    <header class="settings-hero card">
      <div class="settings-avatar">{{ userInitial }}</div>
      <h2>{{ displayName }}</h2>
      <p>{{ maskedAccount }}</p>
    </header>

    <section class="settings-tabs card">
      <div class="settings-tab-row">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="['settings-tab-btn', { active: activeTab === tab.key }]"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="settings-tab-content">
        <section v-if="activeTab === 'accounts'" class="tab-pane">
          <h3>通过以下方式登录</h3>

          <article class="bind-card">
            <div>
              <h4>邮箱账号</h4>
              <p>绑定后可用于登录与找回密码。</p>
            </div>
            <div class="bind-value">{{ user.email || '未绑定' }}</div>
          </article>

          <article class="bind-card">
            <div>
              <h4>用户名</h4>
              <p>可使用用户名或邮箱登录系统。</p>
            </div>
            <div class="bind-value">{{ user.username || '未设置' }}</div>
          </article>
        </section>

        <section v-else-if="activeTab === 'providers'" class="tab-pane">
          <div class="providers-head">
            <div>
              <h3>翻译 API 配置</h3>
              <p class="helper-text">配置 OpenAI 兼容接口用于选中文本翻译。</p>
            </div>
          </div>

          <form class="paper-form" @submit.prevent="onCreateProvider">
            <input v-model="form.name" placeholder="Provider 名称" required />
            <input v-model="form.model" placeholder="模型名，例如 gpt-4.1-mini" required />
            <input v-model="form.base_url" placeholder="Base URL，例如 https://api.openai.com/v1" required />
            <input v-model="form.api_key" placeholder="API Key" required />
            <label class="check-line">
              <input v-model="form.is_default" type="checkbox" />
              设为默认翻译服务
            </label>
            <button type="submit">保存配置</button>
          </form>

          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>名称</th>
                  <th>模型</th>
                  <th>Base URL</th>
                  <th>API Key</th>
                  <th>默认</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="provider in providers" :key="provider.id">
                  <td>{{ provider.name }}</td>
                  <td>{{ provider.model }}</td>
                  <td>{{ provider.base_url }}</td>
                  <td>{{ provider.api_key }}</td>
                  <td>{{ provider.is_default ? '是' : '否' }}</td>
                </tr>
                <tr v-if="providers.length === 0">
                  <td colspan="5">当前还没有配置翻译 API。</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-else-if="activeTab === 'storage'" class="tab-pane">
          <h3>存储设置</h3>
          <div class="placeholder-grid">
            <article>
              <h4>本地缓存</h4>
              <p>当前模式：浏览器本地存储 + 后端 MongoDB。</p>
            </article>
            <article>
              <h4>文件存储路径</h4>
              <p>建议后续接入对象存储（MinIO / S3）以支持多设备同步。</p>
            </article>
          </div>
        </section>

        <section v-else class="tab-pane">
          <h3>账号设置</h3>
          <article v-if="route.query.help === '1'" class="help-focus-card">
            <h4>帮助入口</h4>
            <p>后续这里会集中放置常见问题、工单入口和 API 接入文档。</p>
          </article>
          <div class="placeholder-grid">
            <article>
              <h4>显示名</h4>
              <p>{{ displayName }}</p>
            </article>
            <article>
              <h4>安全提醒</h4>
              <p>建议定期更换密码，并开启双重验证（后续可扩展）。</p>
            </article>
            <article class="appearance-card">
              <h4>外观设置</h4>
              <p>当前主题：{{ isDarkTheme ? "黑夜模式" : "白天模式" }}。主题选择会保存在本地。</p>
              <div class="appearance-actions">
                <button
                  class="btn-secondary"
                  :class="{ active: currentTheme === THEMES.LIGHT }"
                  @click="chooseTheme(THEMES.LIGHT)"
                >
                  ☀️ 白天模式
                </button>
                <button
                  class="btn-secondary"
                  :class="{ active: currentTheme === THEMES.DARK }"
                  @click="chooseTheme(THEMES.DARK)"
                >
                  🌙 黑夜模式
                </button>
              </div>
            </article>
          </div>
        </section>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";

import { createProvider, fetchMe, fetchProviders } from "@/services/api";
import { getUser } from "@/services/auth";
import { THEME_CHANGE_EVENT, THEMES, getStoredTheme, setStoredTheme } from "@/services/theme";

const tabs = [
  { key: "accounts", label: "已绑定账号" },
  { key: "providers", label: "我的配置" },
  { key: "storage", label: "存储设置" },
  { key: "account", label: "账号设置" }
];

const activeTab = ref("accounts");
const providers = ref([]);
const user = ref(getUser() || {});
const route = useRoute();
const currentTheme = ref(getStoredTheme());

const form = reactive({
  name: "",
  model: "",
  base_url: "",
  api_key: "",
  is_default: true
});

const displayName = computed(() => user.value.display_name || user.value.username || "用户");
const isDarkTheme = computed(() => currentTheme.value === THEMES.DARK);

const userInitial = computed(() => {
  const source = user.value.display_name || user.value.username || user.value.email || "U";
  return source.slice(0, 1).toUpperCase();
});

const maskedAccount = computed(() => {
  const raw = user.value.email || user.value.username || "未绑定";
  if (raw.includes("@")) {
    const [name, domain] = raw.split("@");
    const safeName = name.length <= 2 ? `${name[0] || "*"}*` : `${name.slice(0, 2)}***${name.slice(-1)}`;
    return `${safeName}@${domain}`;
  }
  if (raw.length >= 7) return `${raw.slice(0, 3)}****${raw.slice(-2)}`;
  if (raw.length >= 3) return `${raw[0]}***${raw.slice(-1)}`;
  return raw;
});

async function loadProviders() {
  providers.value = await fetchProviders();
}

async function loadUser() {
  try {
    const me = await fetchMe();
    if (me) {
      user.value = me;
    }
  } catch {
    // Keep local cached user when /me is unavailable.
  }
}

async function onCreateProvider() {
  await createProvider({ ...form });
  form.name = "";
  form.model = "";
  form.base_url = "";
  form.api_key = "";
  form.is_default = false;
  await loadProviders();
}

function chooseTheme(theme) {
  currentTheme.value = setStoredTheme(theme);
}

function handleThemeChange(event) {
  currentTheme.value = event?.detail?.theme || getStoredTheme();
}

onMounted(async () => {
  window.addEventListener(THEME_CHANGE_EVENT, handleThemeChange);
  const requestedTab = String(route.query.tab || "");
  if (tabs.some((item) => item.key === requestedTab)) {
    activeTab.value = requestedTab;
  }
  await Promise.all([loadProviders(), loadUser()]);
});

onBeforeUnmount(() => {
  window.removeEventListener(THEME_CHANGE_EVENT, handleThemeChange);
});
</script>
