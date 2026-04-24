const API_STATE = "/api/state";
const STATUS_OPTIONS = ["未开始", "进行中", "阻塞", "已完成"];
const PRIORITY_OPTIONS = ["低", "中", "高", "关键"];
const CADENCE_OPTIONS = ["每日推进", "每周推进", "双周复盘", "里程碑驱动"];
const COLOR_OPTIONS = [
  { value: "red", label: "红色重点", tone: "danger" },
  { value: "yellow", label: "黄色关注", tone: "warning" },
  { value: "green", label: "绿色常规", tone: "success" },
];
const MILESTONE_ICONS = [
  { value: "target", symbol: "🎯", label: "目标" },
  { value: "flag", symbol: "🚩", label: "标记" },
  { value: "rocket", symbol: "🚀", label: "推进" },
  { value: "spark", symbol: "✨", label: "成果" },
  { value: "alert", symbol: "⚠️", label: "风险" },
  { value: "check", symbol: "✅", label: "验收" },
  { value: "doc", symbol: "📝", label: "文档" },
];
const TIMELINE_ZOOM_LEVELS = [48, 64, 84, 108];
const APP_VERSION = "2026.03.22-2";

function uid() {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (char) => {
    const random = (Math.random() * 16) | 0;
    const value = char === "x" ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}

function startOfDay(input) {
  const date = new Date(input);
  date.setHours(0, 0, 0, 0);
  return date;
}

function parseDate(value, fallback = new Date()) {
  if (!value) return startOfDay(fallback);
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? startOfDay(fallback) : startOfDay(parsed);
}

function addDays(input, days) {
  const date = new Date(input);
  date.setDate(date.getDate() + days);
  return startOfDay(date);
}

function diffDays(a, b) {
  return Math.round((startOfDay(a).getTime() - startOfDay(b).getTime()) / 86400000);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function formatDate(input) {
  const date = startOfDay(input);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatShortDate(value) {
  const date = parseDate(value);
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

function getIsoWeekNumber(value) {
  const date = parseDate(value);
  const target = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = target.getUTCDay() || 7;
  target.setUTCDate(target.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(target.getUTCFullYear(), 0, 1));
  return Math.ceil((((target - yearStart) / 86400000) + 1) / 7);
}

function weekLabel(value) {
  return `W${getIsoWeekNumber(value)}`;
}

function weekdayLabel(value) {
  return parseDate(value).toLocaleDateString("en-US", { weekday: "short" });
}

function formatDisplayDate(value) {
  return `${weekLabel(value)} ${formatShortDate(value)} ${weekdayLabel(value)}`;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function displayText(value, fallback = "未设置") {
  return value && String(value).trim() ? String(value).trim() : fallback;
}

function getIconMeta(value) {
  return MILESTONE_ICONS.find((item) => item.value === value) || MILESTONE_ICONS[0];
}

function getColorMeta(value) {
  return COLOR_OPTIONS.find((item) => item.value === value) || COLOR_OPTIONS[1];
}

function getStatusProgress(status) {
  if (status === "已完成") return 100;
  if (status === "进行中") return 50;
  if (status === "阻塞") return 25;
  return 0;
}

function computeProgress(milestones, manualProgress) {
  if (!milestones.length) return clamp(Number(manualProgress || 0), 0, 100);
  const doneCount = milestones.filter((item) => item.done).length;
  return Math.round((doneCount / milestones.length) * 100);
}

function sanitizeMilestone(item) {
  return {
    id: item && item.id ? item.id : uid(),
    title: item && item.title ? item.title : "未命名节点",
    dueDate: item && item.dueDate ? item.dueDate : "",
    done: Boolean(item && item.done),
    icon: getIconMeta(item && item.icon ? item.icon : "target").value,
  };
}

function sanitizeCategory(item) {
  return {
    id: item && item.id ? item.id : uid(),
    project: item && item.project ? item.project : "",
    name: item && item.name ? item.name : "",
    order: Number.isFinite(Number(item && item.order)) ? Number(item.order) : 0,
  };
}

function categoryLabel(category, includeProject = false) {
  if (!category) return "未设置";
  return includeProject ? `${displayText(category.project)} / ${displayText(category.name)}` : displayText(category.name);
}

function getCategoryById(categoryId) {
  return state.data.categories.find((item) => item.id === categoryId) || null;
}

function getCategoriesForProject(projectName) {
  return state.data.categories
    .filter((item) => item.project === projectName)
    .sort((a, b) => a.order - b.order || a.name.localeCompare(b.name, "zh-CN"));
}

function getCategoryRecord(projectName, categoryName) {
  return state.data.categories.find((item) => item.project === projectName && item.name === categoryName) || null;
}

function getVisibleCategoryOptions() {
  if (state.filters.project !== "全部项目") {
    return getCategoriesForProject(state.filters.project);
  }
  return state.data.categories;
}

function renderCategoryOptions(projectName, selectedCategoryName = "") {
  return getCategoriesForProject(projectName)
    .map((item) => `<option value="${escapeHtml(item.id)}" ${item.name === selectedCategoryName && item.project === projectName ? "selected" : ""}>${escapeHtml(item.name)}</option>`)
    .join("");
}

function sanitizePlan(plan) {
  const today = startOfDay(new Date());
  const startDate = parseDate(plan && plan.startDate, today);
  const endDateCandidate = parseDate(plan && plan.endDate, startDate);
  const endDate = diffDays(endDateCandidate, startDate) < 0 ? startDate : endDateCandidate;
  const milestones = Array.isArray(plan && plan.milestones) ? plan.milestones.map(sanitizeMilestone) : [];
  const updates = Array.isArray(plan && plan.updates)
    ? plan.updates.map((item) => ({
        id: item.id || uid(),
        date: item.date || formatDate(today),
        text: item.text || "",
      }))
    : [];

  return {
    id: (plan && plan.id) || uid(),
    title: (plan && plan.title) || "未命名计划",
    project: (plan && plan.project) || "",
    category: (plan && plan.category) || "",
    cadence: CADENCE_OPTIONS.includes(plan && plan.cadence) ? plan.cadence : "每周推进",
    startDate: formatDate(startDate),
    endDate: formatDate(endDate),
    priority: PRIORITY_OPTIONS.includes(plan && plan.priority) ? plan.priority : "中",
    status: STATUS_OPTIONS.includes(plan && plan.status) ? plan.status : "未开始",
    owner: (plan && plan.owner) || "",
    progress: computeProgress(milestones, plan && plan.progress != null ? plan.progress : getStatusProgress(plan && plan.status)),
    notes: (plan && plan.notes) || "",
    nextAction: (plan && plan.nextAction) || "",
    successMetric: (plan && plan.successMetric) || "",
    markColor: getColorMeta(plan && plan.markColor ? plan.markColor : "yellow").value,
    order: Number.isFinite(Number(plan && plan.order)) ? Number(plan.order) : 0,
    milestones,
    updates,
  };
}

function normalizeData(data) {
  const plans = (Array.isArray(data && data.plans) ? data.plans.map(sanitizePlan) : [])
    .sort((a, b) => a.order - b.order || a.title.localeCompare(b.title, "zh-CN"));
  const rawCategories = Array.isArray(data && data.categories)
    ? data.categories.map(sanitizeCategory)
    : plans
        .filter((plan) => plan.project && plan.category)
        .map((plan, index) => sanitizeCategory({ project: plan.project, name: plan.category, order: index }));
  const categories = rawCategories
    .filter((item, index, items) => item.project && item.name && items.findIndex((other) => other.project === item.project && other.name === item.name) === index)
    .sort((a, b) => a.project.localeCompare(b.project, "zh-CN") || a.order - b.order || a.name.localeCompare(b.name, "zh-CN"));
  const projects = Array.from(new Set([...(Array.isArray(data && data.projects) ? data.projects : []), ...plans.map((plan) => plan.project).filter(Boolean)]));
  return { categories, projects, plans };
}

function getEmptyState() {
  return { categories: [], projects: [], plans: [] };
}

const state = {
  data: getEmptyState(),
  filters: {
    search: "",
    project: "全部项目",
    category: "全部分类",
    status: "全部状态",
  },
  selectedPlanId: "",
  selectedProjectName: "",
  selectedCategoryKey: "",
  expandedProjects: [],
  expandedCategoryKeys: [],
  composerOpen: false,
  composerMode: "plan",
  editingPlanId: null,
  editingProjectName: "",
  editingCategoryId: "",
  milestonePlanId: null,
  editingMilestoneId: null,
  loaded: false,
  saving: false,
  error: "",
  timelineZoom: 1,
  timelineAnchorDate: formatDate(new Date()),
  saveQueue: Promise.resolve(),
};

function getCategoryKey(projectName, categoryName) {
  return `${projectName}::${categoryName}`;
}

function toggleExpandedProject(projectName) {
  state.expandedProjects = state.expandedProjects.includes(projectName)
    ? state.expandedProjects.filter((item) => item !== projectName)
    : [...state.expandedProjects, projectName];
}

function toggleExpandedCategory(projectName, categoryName) {
  const key = getCategoryKey(projectName, categoryName);
  state.expandedCategoryKeys = state.expandedCategoryKeys.includes(key)
    ? state.expandedCategoryKeys.filter((item) => item !== key)
    : [...state.expandedCategoryKeys, key];
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function loadState() {
  try {
    const payload = await requestJson(API_STATE);
    state.data = normalizeData(payload);
    state.loaded = true;
    state.error = "";
  } catch (error) {
    state.data = getEmptyState();
    state.loaded = true;
    state.error = "数据库读取失败，请确认本地服务已经启动。";
  }
  render();
}

async function shutdownApp() {
  try {
    await requestJson("/api/shutdown", { method: "POST" });
  } catch {
    // Ignore shutdown request errors and still try to close the page.
  }
  window.open("", "_self");
  window.close();
}

function persistState() {
  state.saving = true;
  render();
  state.saveQueue = state.saveQueue
    .then(() =>
      requestJson(API_STATE, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(normalizeData(state.data)),
      }),
    )
    .then(() => {
      state.saving = false;
      state.error = "";
      render();
    })
    .catch(() => {
      state.saving = false;
      state.error = "数据库保存失败，请检查服务是否仍在运行。";
      render();
    });
}

function badge(label, tone) {
  return `<span class="badge badge-${tone}">${escapeHtml(label)}</span>`;
}

function colorPill(markColor) {
  const meta = getColorMeta(markColor);
  return `<span class="color-pill color-${meta.value}">${escapeHtml(meta.label)}</span>`;
}

function milestoneIcon(icon) {
  const meta = getIconMeta(icon);
  return `<span class="milestone-icon" title="${escapeHtml(meta.label)}">${meta.symbol}</span>`;
}

function getStatusMeta(status) {
  if (status === "已完成") return { label: "已完成", tone: "success" };
  if (status === "阻塞") return { label: "阻塞", tone: "danger" };
  if (status === "进行中") return { label: "进行中", tone: "accent" };
  return { label: "未开始", tone: "muted" };
}

function getPriorityMeta(priority) {
  if (priority === "关键") return { label: "关键", tone: "danger" };
  if (priority === "高") return { label: "高", tone: "warning" };
  if (priority === "中") return { label: "中", tone: "accent" };
  return { label: "低", tone: "muted" };
}

function daysLeft(dateString) {
  return diffDays(dateString, new Date());
}

function isOverdue(plan) {
  return plan.status !== "已完成" && daysLeft(plan.endDate) < 0;
}

function getTimelineBounds(plans) {
  const today = startOfDay(new Date());
  if (!plans.length) {
    return { start: addDays(today, -3), end: addDays(today, 24) };
  }
  let start = parseDate(plans[0].startDate);
  let end = parseDate(plans[0].endDate);
  plans.forEach((plan) => {
    const planStart = parseDate(plan.startDate);
    const planEnd = parseDate(plan.endDate);
    if (planStart < start) start = planStart;
    if (planEnd > end) end = planEnd;
  });
  if (today < start) start = today;
  if (today > end) end = today;
  return { start: addDays(start, -2), end: addDays(end, 6) };
}

function createDateRange(start, end) {
  const total = diffDays(end, start) + 1;
  return Array.from({ length: total }, (_, index) => addDays(start, index));
}

function getFilteredPlans() {
  const selectedCategory = state.filters.category === "全部分类" ? null : getCategoryById(state.filters.category);
  return state.data.plans.filter((plan) => {
    const haystack = [plan.title, plan.project, plan.category, plan.notes, plan.nextAction, plan.successMetric].join(" ").toLowerCase();
    return (
      haystack.includes(state.filters.search.toLowerCase()) &&
      (state.filters.project === "全部项目" || plan.project === state.filters.project) &&
      (!selectedCategory || (plan.project === selectedCategory.project && plan.category === selectedCategory.name)) &&
      (state.filters.status === "全部状态" || plan.status === state.filters.status)
    );
  });
}

function getSelectedPlan(filteredPlans) {
  return filteredPlans.find((plan) => plan.id === state.selectedPlanId) || null;
}

function getMetrics(plans) {
  const total = plans.length;
  const active = plans.filter((plan) => plan.status === "进行中").length;
  const completed = plans.filter((plan) => plan.status === "已完成").length;
  const risks = plans.filter((plan) => plan.status === "阻塞" || isOverdue(plan)).length;
  const avgProgress = total ? Math.round(plans.reduce((sum, plan) => sum + getPlanProgress(plan), 0) / total) : 0;
  return { total, active, completed, risks, avgProgress };
}

function getPlanProgress(plan) {
  return computeProgress(plan.milestones, getStatusProgress(plan.status));
}

function getCategoryProgress(projectName, categoryName) {
  const plans = state.data.plans.filter((plan) => plan.project === projectName && plan.category === categoryName);
  return plans.length ? Math.round(plans.reduce((sum, plan) => sum + getPlanProgress(plan), 0) / plans.length) : 0;
}

function getProjectProgress(projectName) {
  const plans = state.data.plans.filter((plan) => plan.project === projectName);
  return plans.length ? Math.round(plans.reduce((sum, plan) => sum + getPlanProgress(plan), 0) / plans.length) : 0;
}

function openComposer(planId) {
  state.composerMode = "plan";
  state.editingPlanId = planId || null;
  state.milestonePlanId = null;
  state.editingMilestoneId = null;
  state.composerOpen = true;
  render();
}

function openProjectComposer() {
  state.composerMode = "project";
  state.editingProjectName = "";
  state.editingCategoryId = "";
  state.editingPlanId = null;
  state.milestonePlanId = null;
  state.editingMilestoneId = null;
  state.composerOpen = true;
  render();
}

function openProjectEditor(projectName) {
  state.composerMode = "project";
  state.editingProjectName = projectName || "";
  state.editingCategoryId = "";
  state.editingPlanId = null;
  state.milestonePlanId = null;
  state.editingMilestoneId = null;
  state.composerOpen = true;
  render();
}

function openCategoryComposer() {
  state.composerMode = "category";
  state.editingProjectName = "";
  state.editingCategoryId = "";
  state.editingPlanId = null;
  state.milestonePlanId = null;
  state.editingMilestoneId = null;
  state.composerOpen = true;
  render();
}

function openCategoryEditor(categoryId) {
  state.composerMode = "category";
  state.editingProjectName = "";
  state.editingCategoryId = categoryId || "";
  state.editingPlanId = null;
  state.milestonePlanId = null;
  state.editingMilestoneId = null;
  state.composerOpen = true;
  render();
}

function openMilestoneComposer(planId, milestoneId = null) {
  state.composerMode = "milestone";
  state.editingPlanId = null;
  state.milestonePlanId = planId;
  state.editingMilestoneId = milestoneId;
  state.composerOpen = true;
  render();
}

function closeComposer() {
  state.editingPlanId = null;
  state.editingProjectName = "";
  state.editingCategoryId = "";
  state.composerOpen = false;
  state.composerMode = "plan";
  state.milestonePlanId = null;
  state.editingMilestoneId = null;
  render();
}

function getCurrentEditingPlan() {
  if (!state.editingPlanId) return null;
  return state.data.plans.find((plan) => plan.id === state.editingPlanId) || null;
}

function updateData(updater) {
  state.data = normalizeData(updater(state.data));
  persistState();
}

function resequence(items) {
  return items.map((item, index) => ({ ...item, order: index }));
}

function moveCategory(categoryId, targetCategoryId) {
  if (!categoryId || !targetCategoryId || categoryId === targetCategoryId) return;
  updateData((data) => {
    const moving = data.categories.find((item) => item.id === categoryId);
    const target = data.categories.find((item) => item.id === targetCategoryId);
    if (!moving || !target || moving.project !== target.project) return data;
    const siblings = data.categories.filter((item) => item.project === moving.project).sort((a, b) => a.order - b.order);
    const movingIndex = siblings.findIndex((item) => item.id === categoryId);
    const targetIndex = siblings.findIndex((item) => item.id === targetCategoryId);
    if (movingIndex < 0 || targetIndex < 0) return data;
    const next = [...siblings];
    const [item] = next.splice(movingIndex, 1);
    next.splice(targetIndex, 0, item);
    const resequenced = resequence(next);
    return {
      ...data,
      categories: data.categories.map((item) => resequenced.find((candidate) => candidate.id === item.id) || item),
    };
  });
  render();
}

function movePlan(planId, targetPlanId) {
  if (!planId || !targetPlanId || planId === targetPlanId) return;
  updateData((data) => {
    const moving = data.plans.find((item) => item.id === planId);
    const target = data.plans.find((item) => item.id === targetPlanId);
    if (!moving || !target || moving.project !== target.project || moving.category !== target.category) return data;
    const siblings = data.plans
      .filter((item) => item.project === moving.project && item.category === moving.category)
      .sort((a, b) => a.order - b.order);
    const movingIndex = siblings.findIndex((item) => item.id === planId);
    const targetIndex = siblings.findIndex((item) => item.id === targetPlanId);
    if (movingIndex < 0 || targetIndex < 0) return data;
    const next = [...siblings];
    const [item] = next.splice(movingIndex, 1);
    next.splice(targetIndex, 0, item);
    const resequenced = resequence(next);
    return {
      ...data,
      plans: data.plans.map((item) => resequenced.find((candidate) => candidate.id === item.id) || item),
    };
  });
  render();
}

function savePlan(plan) {
  const sanitized = sanitizePlan(plan);
  updateData((data) => {
    const exists = data.plans.some((item) => item.id === sanitized.id);
    const nextPlan = exists
      ? sanitized
      : {
          ...sanitized,
          order: data.plans.filter((item) => item.project === sanitized.project && item.category === sanitized.category).length,
        };
    const plans = exists ? data.plans.map((item) => (item.id === nextPlan.id ? nextPlan : item)) : [...data.plans, nextPlan];
    return { ...data, plans };
  });
  state.selectedPlanId = sanitized.id;
  state.selectedProjectName = sanitized.project;
  state.selectedCategoryKey = getCategoryKey(sanitized.project, sanitized.category);
  state.composerOpen = false;
  state.editingPlanId = null;
  render();
}

function deletePlan(planId) {
  updateData((data) => ({ ...data, plans: data.plans.filter((item) => item.id !== planId) }));
  if (state.selectedPlanId === planId) {
    state.selectedPlanId = "";
  }
  render();
}

function toggleMilestone(planId, milestoneId) {
  updateData((data) => ({
    ...data,
    plans: data.plans.map((plan) => {
      if (plan.id !== planId) return plan;
      const milestones = plan.milestones.map((item) => (item.id === milestoneId ? { ...item, done: !item.done } : item));
      const progress = computeProgress(milestones, getStatusProgress(plan.status));
      const status = progress === 100 ? "已完成" : plan.status === "未开始" ? "进行中" : plan.status;
      return { ...plan, milestones, progress, status };
    }),
  }));
  render();
}

function saveMilestone(planId, milestoneInput) {
  const milestone = sanitizeMilestone(milestoneInput);
  updateData((data) => ({
    ...data,
    plans: data.plans.map((plan) => {
      if (plan.id !== planId) return plan;
      const exists = plan.milestones.some((item) => item.id === milestone.id);
      const milestones = exists ? plan.milestones.map((item) => (item.id === milestone.id ? { ...item, ...milestone } : item)) : [...plan.milestones, milestone];
      const progress = computeProgress(milestones, getStatusProgress(plan.status));
      const status = progress === 100 ? "已完成" : plan.status === "未开始" ? "进行中" : plan.status;
      return { ...plan, milestones, progress, status };
    }),
  }));
  state.composerOpen = false;
  state.composerMode = "plan";
  state.milestonePlanId = null;
  state.editingMilestoneId = null;
  render();
}

function deleteMilestone(planId, milestoneId) {
  updateData((data) => ({
    ...data,
    plans: data.plans.map((plan) => {
      if (plan.id !== planId) return plan;
      const milestones = plan.milestones.filter((item) => item.id !== milestoneId);
      const progress = computeProgress(milestones, getStatusProgress(plan.status));
      return { ...plan, milestones, progress };
    }),
  }));
  render();
}

function addUpdate(planId, text) {
  if (!text.trim()) return;
  updateData((data) => ({
    ...data,
    plans: data.plans.map((plan) =>
      plan.id === planId
        ? {
            ...plan,
            updates: [{ id: uid(), date: formatDate(new Date()), text: text.trim() }, ...plan.updates],
            status: plan.status === "未开始" ? "进行中" : plan.status,
          }
        : plan,
    ),
  }));
  render();
}

function addProject(name) {
  if (!name.trim()) return;
  updateData((data) => ({ ...data, projects: Array.from(new Set([...data.projects, name.trim()])) }));
  state.composerOpen = false;
  state.composerMode = "plan";
  render();
}

function saveProject(originalName, nextName) {
  const trimmedOriginal = String(originalName || "").trim();
  const trimmedNext = String(nextName || "").trim();
  if (!trimmedNext) return;
  if (!trimmedOriginal || trimmedOriginal === trimmedNext) {
    addProject(trimmedNext);
    return;
  }
  updateData((data) => ({
    ...data,
    projects: Array.from(new Set(data.projects.map((item) => (item === trimmedOriginal ? trimmedNext : item)))),
    categories: data.categories.map((item) => (item.project === trimmedOriginal ? { ...item, project: trimmedNext } : item)),
    plans: data.plans.map((plan) => (plan.project === trimmedOriginal ? { ...plan, project: trimmedNext } : plan)),
  }));
  if (state.filters.project === trimmedOriginal) state.filters.project = trimmedNext;
  if (state.selectedProjectName === trimmedOriginal) state.selectedProjectName = trimmedNext;
  if (state.selectedCategoryKey) {
    const [projectName, categoryName] = state.selectedCategoryKey.split("::");
    if (projectName === trimmedOriginal) state.selectedCategoryKey = getCategoryKey(trimmedNext, categoryName);
  }
  state.expandedProjects = state.expandedProjects.map((item) => (item === trimmedOriginal ? trimmedNext : item));
  state.expandedCategoryKeys = state.expandedCategoryKeys.map((key) => {
    const [projectName, categoryName] = key.split("::");
    return projectName === trimmedOriginal ? getCategoryKey(trimmedNext, categoryName) : key;
  });
  state.composerOpen = false;
  state.composerMode = "plan";
  state.editingProjectName = "";
  render();
}

function addCategory(projectName, categoryName) {
  if (!projectName.trim() || !categoryName.trim()) return;
  updateData((data) => ({
    ...data,
    categories: normalizeData({
      ...data,
      categories: [...data.categories, { id: uid(), project: projectName.trim(), name: categoryName.trim(), order: data.categories.filter((item) => item.project === projectName.trim()).length }],
    }).categories,
  }));
  state.composerOpen = false;
  state.composerMode = "plan";
  render();
}

function saveCategory(categoryId, projectName, categoryName) {
  const trimmedProject = String(projectName || "").trim();
  const trimmedName = String(categoryName || "").trim();
  if (!trimmedProject || !trimmedName) return;
  if (!categoryId) {
    addCategory(trimmedProject, trimmedName);
    return;
  }
  const existing = getCategoryById(categoryId);
  if (!existing) return;
  updateData((data) => ({
    ...data,
    categories: normalizeData({
      ...data,
      categories: data.categories.map((item) => (item.id === categoryId ? { ...item, project: trimmedProject, name: trimmedName } : item)),
    }).categories,
    plans: data.plans.map((plan) => (plan.project === existing.project && plan.category === existing.name ? { ...plan, project: trimmedProject, category: trimmedName } : plan)),
  }));
  if (state.filters.category === categoryId) state.filters.project = trimmedProject;
  if (state.selectedCategoryKey === getCategoryKey(existing.project, existing.name)) {
    state.selectedCategoryKey = getCategoryKey(trimmedProject, trimmedName);
  }
  if (state.selectedProjectName === existing.project) state.selectedProjectName = trimmedProject;
  state.expandedCategoryKeys = state.expandedCategoryKeys.map((key) => (key === getCategoryKey(existing.project, existing.name) ? getCategoryKey(trimmedProject, trimmedName) : key));
  state.composerOpen = false;
  state.composerMode = "plan";
  state.editingCategoryId = "";
  render();
}

function deleteProject(projectName) {
  if (!projectName) return;
  updateData((data) => ({
    ...data,
    projects: data.projects.filter((item) => item !== projectName),
    categories: data.categories.filter((item) => item.project !== projectName),
    plans: data.plans.filter((plan) => plan.project !== projectName),
  }));
  if (state.filters.project === projectName) {
    state.filters.project = "全部项目";
    state.filters.category = "全部分类";
  }
  if (state.selectedProjectName === projectName) {
    state.selectedProjectName = "";
    state.selectedCategoryKey = "";
    state.selectedPlanId = "";
  }
  render();
}

function deleteCategory(categoryId) {
  const category = getCategoryById(categoryId);
  if (!category) return;
  updateData((data) => ({
    ...data,
    categories: data.categories.filter((item) => item.id !== categoryId),
    plans: data.plans.filter((plan) => !(plan.project === category.project && plan.category === category.name)),
  }));
  if (state.filters.category === categoryId) {
    state.filters.category = "全部分类";
  }
  if (state.selectedCategoryKey === getCategoryKey(category.project, category.name)) {
    state.selectedCategoryKey = "";
    state.selectedPlanId = "";
  }
  render();
}

function renderStructureManager() {
  return `
    <div class="surface structure-panel">
      <div class="section-head">
        <div>
          <div class="section-kicker">Structure</div>
          <h3 class="subsection-title">项目与工作分类</h3>
        </div>
      </div>
      ${
        state.data.projects.length
          ? `<div class="structure-list">
              ${state.data.projects
                .map((projectName) => {
                  const categories = getCategoriesForProject(projectName);
                  const planCount = state.data.plans.filter((plan) => plan.project === projectName).length;
                  return `
                    <div class="structure-card">
                      <div class="structure-head">
                        <div>
                          <div class="structure-title">${escapeHtml(projectName)}</div>
                          <div class="structure-meta">${categories.length} 个工作分类 · ${planCount} 条计划</div>
                        </div>
                        <div class="inline-row">
                          <button type="button" class="button-ghost" data-action="edit-project" data-project-name="${escapeHtml(projectName)}">编辑项目</button>
                          <button type="button" class="button-ghost danger-ghost" data-action="delete-project" data-project-name="${escapeHtml(projectName)}">删除项目</button>
                        </div>
                      </div>
                      <div class="structure-children">
                        ${
                          categories.length
                            ? categories
                                .map((category) => {
                                  const childPlanCount = state.data.plans.filter((plan) => plan.project === category.project && plan.category === category.name).length;
                                  return `
                                    <div class="structure-child">
                                      <div>
                                        <div class="structure-child-title">${escapeHtml(category.name)}</div>
                                        <div class="structure-meta">${childPlanCount} 条计划</div>
                                      </div>
                                      <div class="inline-row">
                                        <button type="button" class="button-ghost" data-action="edit-category" data-category-id="${escapeHtml(category.id)}">编辑分类</button>
                                        <button type="button" class="button-ghost danger-ghost" data-action="delete-category" data-category-id="${escapeHtml(category.id)}">删除分类</button>
                                      </div>
                                    </div>
                                  `;
                                })
                                .join("")
                            : `<div class="empty-copy">这个项目下还没有工作分类。</div>`
                        }
                      </div>
                    </div>
                  `;
                })
                .join("")}
            </div>`
          : `<div class="empty-state">还没有项目结构。建议先新建项目，再在项目下创建工作分类。</div>`
      }
    </div>
  `;
}

function renderStats(metrics) {
  const cards = [
    { label: "计划总数", value: metrics.total, copy: "当前数据库中的有效计划" },
    { label: "进行中", value: metrics.active, copy: "适合每日回看推进节奏" },
    { label: "平均进度", value: `${metrics.avgProgress}%`, copy: "衡量整体执行温度" },
    { label: "风险项", value: metrics.risks, copy: "阻塞和逾期的计划总数" },
    { label: "已完成", value: metrics.completed, copy: "用于周报或月度复盘" },
  ];
  return `
    <section class="stats">
      ${cards
        .map(
          (card) => `
            <div class="surface stat-card">
              <div class="stat-label">${escapeHtml(card.label)}</div>
              <div class="stat-value">${escapeHtml(card.value)}</div>
              <div class="stat-copy">${escapeHtml(card.copy)}</div>
            </div>
          `,
        )
        .join("")}
    </section>
  `;
}

function renderWorkspace(filteredPlans, selectedPlan) {
  const detailHtml = renderDetail(selectedPlan);
  return `
    <section class="workspace surface">
      <div class="workspace-head">
        <div>
          <div class="section-kicker">Workspace</div>
          <h2 class="section-title">工作计划台</h2>
        </div>
        <div class="workspace-actions">
          <div class="save-state ${state.saving ? "is-saving" : ""}">${state.saving ? "保存中" : "已连接数据库"}</div>
          <button type="button" class="button-ghost" data-action="open-project-create">新建项目</button>
          <button type="button" class="button-ghost" data-action="open-category-create">新建工作分类</button>
          <button type="button" class="button-primary" data-action="open-create">新建计划</button>
        </div>
      </div>
      ${state.error ? `<div class="banner-error">${escapeHtml(state.error)}</div>` : ""}
      <div class="color-guide">
        ${COLOR_OPTIONS.map((item) => `<span class="color-guide-item color-${item.value}">${escapeHtml(item.label)}</span>`).join("")}
      </div>
      <div class="filters">
        <label class="field">
          <span class="field-label">搜索</span>
          <input id="search-input" class="field-control" placeholder="搜索标题、备注、下一步动作" value="${escapeHtml(state.filters.search)}" />
        </label>
        <label class="field">
          <span class="field-label">项目</span>
          <select id="project-filter" class="field-control">
            <option value="全部项目">全部项目</option>
            ${state.data.projects.map((item) => `<option value="${escapeHtml(item)}" ${item === state.filters.project ? "selected" : ""}>${escapeHtml(item)}</option>`).join("")}
          </select>
        </label>
        <label class="field">
          <span class="field-label">工作分类</span>
          <select id="category-filter" class="field-control">
            <option value="全部分类">全部分类</option>
            ${getVisibleCategoryOptions().map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === state.filters.category ? "selected" : ""}>${escapeHtml(categoryLabel(item, state.filters.project === "全部项目"))}</option>`).join("")}
          </select>
        </label>
        <label class="field">
          <span class="field-label">状态</span>
          <select id="status-filter" class="field-control">
            <option value="全部状态">全部状态</option>
            ${STATUS_OPTIONS.map((item) => `<option value="${escapeHtml(item)}" ${item === state.filters.status ? "selected" : ""}>${escapeHtml(item)}</option>`).join("")}
          </select>
        </label>
      </div>
      <div class="dashboard">
        <div>${renderPlanList(filteredPlans, selectedPlan)}</div>
        ${detailHtml ? `<div>${detailHtml}</div>` : ""}
      </div>
      ${renderStructureManager()}
    </section>
  `;
}

function renderPlanList(filteredPlans, selectedPlan) {
  if (!filteredPlans.length) {
    return `<div class="empty-state">还没有任何计划。你可以直接点击“新建计划”，内容会保存到本地 SQLite 数据库。</div>`;
  }

  const projectNames = Array.from(new Set(filteredPlans.map((plan) => plan.project).filter(Boolean)));
  return `
    <div class="tree-list">
      ${projectNames
        .map((projectName) => {
          const projectPlans = filteredPlans.filter((plan) => plan.project === projectName);
          const categories = getCategoriesForProject(projectName)
            .map((item) => item.name)
            .filter((name) => projectPlans.some((plan) => plan.category === name));
          const projectExpanded = state.expandedProjects.includes(projectName);
          return `
            <div class="tree-project">
              <div class="tree-row-shell">
                <button type="button" class="tree-project-row ${state.selectedProjectName === projectName && !state.selectedCategoryKey && !state.selectedPlanId ? "active" : ""}" data-action="select-project-node" data-project-name="${escapeHtml(projectName)}">
                  <span class="tree-caret">${projectExpanded ? "▾" : "▸"}</span>
                  <span class="tree-project-title">${escapeHtml(projectName)}</span>
                  <span class="tree-count">${getProjectProgress(projectName)}% · ${projectPlans.length}</span>
                </button>
                <button type="button" class="button-ghost tree-inline-action" data-action="edit-project" data-project-name="${escapeHtml(projectName)}">编辑</button>
              </div>
              ${
                projectExpanded
                  ? `<div class="tree-children">
                      ${categories
                        .map((categoryName) => {
                          const categoryPlans = projectPlans.filter((plan) => plan.category === categoryName);
                          const categoryKey = getCategoryKey(projectName, categoryName);
                          const categoryExpanded = state.expandedCategoryKeys.includes(categoryKey);
                          return `
                            <div class="tree-category">
                              <div class="tree-row-shell">
                                <button type="button" class="tree-category-row ${state.selectedCategoryKey === categoryKey && !state.selectedPlanId ? "active" : ""}" data-action="select-category-node" data-project-name="${escapeHtml(projectName)}" data-category-name="${escapeHtml(categoryName)}">
                                  <span class="tree-caret">${categoryExpanded ? "▾" : "▸"}</span>
                                  <span class="tree-category-title">${escapeHtml(categoryName)}</span>
                                  <span class="tree-count">${getCategoryProgress(projectName, categoryName)}% · ${categoryPlans.length}</span>
                                </button>
                                <button type="button" class="button-ghost tree-inline-action" data-action="edit-category" data-category-id="${escapeHtml((getCategoryRecord(projectName, categoryName) || {}).id || "")}">编辑</button>
                              </div>
                              ${
                                categoryExpanded
                                  ? `<div class="tree-plan-list">
                                      ${categoryPlans
                                        .sort((a, b) => a.order - b.order || a.title.localeCompare(b.title, "zh-CN"))
                                        .map((plan) => {
                                          const statusMeta = getStatusMeta(plan.status);
                                          const colorMeta = getColorMeta(plan.markColor);
                                          return `
                                            <button type="button" class="tree-plan-row ${selectedPlan && selectedPlan.id === plan.id ? "active" : ""} color-${colorMeta.value}" data-action="select-plan" data-plan-id="${plan.id}">
                                              <span class="tree-plan-accent color-${colorMeta.value}"></span>
                                              <span class="tree-plan-main">
                                                <span class="tree-plan-title">${escapeHtml(plan.title)}</span>
                                                <span class="tree-plan-meta">${escapeHtml(plan.status)} · ${getPlanProgress(plan)}%</span>
                                              </span>
                                              <span class="tree-plan-badges">
                                                ${badge(statusMeta.label, statusMeta.tone)}
                                              </span>
                                            </button>
                                          `;
                                        })
                                        .join("")}
                                    </div>`
                                  : ""
                              }
                            </div>
                          `;
                        })
                        .join("")}
                    </div>`
                  : ""
              }
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderProjectDetail(projectName) {
  const plans = state.data.plans.filter((plan) => plan.project === projectName);
  const categories = getCategoriesForProject(projectName);
  return `
    <div class="detail-stack">
      <div class="surface">
        <div class="section-kicker">Project</div>
        <h2 class="section-title">${escapeHtml(projectName)}</h2>
        <div class="detail-actions" style="margin-top:12px;">
          <span></span>
          <button type="button" class="button-ghost" data-action="edit-project" data-project-name="${escapeHtml(projectName)}">编辑项目</button>
        </div>
        <div class="detail-grid progress-grid">
          <div class="detail-box">
            <div class="detail-label">项目进度</div>
            <div class="detail-value">${getProjectProgress(projectName)}%</div>
            <div class="detail-subvalue">项目下所有计划平均值</div>
          </div>
          <div class="detail-box">
            <div class="detail-label">结构统计</div>
            <div class="detail-value">${categories.length} / ${plans.length}</div>
            <div class="detail-subvalue">工作分类数 / 计划数</div>
          </div>
        </div>
        <div class="detail-box">
          <div class="detail-label">进度标准</div>
          <div class="detail-copy">项目进度按项目下所有计划平均值计算。计划进度优先使用关键节点完成率；没有关键节点时按状态映射：未开始 0%，进行中 50%，阻塞 25%，已完成 100%。</div>
        </div>
      </div>
    </div>
  `;
}

function renderCategoryDetail(projectName, categoryName) {
  const plans = state.data.plans.filter((plan) => plan.project === projectName && plan.category === categoryName);
  const category = getCategoryRecord(projectName, categoryName);
  return `
    <div class="detail-stack">
      <div class="surface">
        <div class="section-kicker">Category</div>
        <h2 class="section-title">${escapeHtml(categoryName)}</h2>
        <div class="detail-subvalue">${escapeHtml(projectName)}</div>
        <div class="detail-actions" style="margin-top:12px;">
          <span></span>
          <button type="button" class="button-ghost" data-action="edit-category" data-category-id="${escapeHtml(category ? category.id : "")}">编辑分类</button>
        </div>
        <div class="detail-grid progress-grid">
          <div class="detail-box">
            <div class="detail-label">工作分类进度</div>
            <div class="detail-value">${getCategoryProgress(projectName, categoryName)}%</div>
            <div class="detail-subvalue">该分类下所有计划平均值</div>
          </div>
          <div class="detail-box">
            <div class="detail-label">计划数</div>
            <div class="detail-value">${plans.length}</div>
            <div class="detail-subvalue">当前工作分类下的计划总数</div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderPlanDetail(selectedPlan) {
  const projectProgress = getProjectProgress(selectedPlan.project);
  const categoryProgress = getCategoryProgress(selectedPlan.project, selectedPlan.category);
  const planProgress = getPlanProgress(selectedPlan);

  return `
    <div class="detail-stack">
      <div class="surface">
        <div class="section-kicker">Detail</div>
        <h2 class="section-title">${escapeHtml(selectedPlan.title)}</h2>
        <div class="plan-tags" style="margin-top:18px;">
          ${colorPill(selectedPlan.markColor)}
          ${badge(getStatusMeta(selectedPlan.status).label, getStatusMeta(selectedPlan.status).tone)}
          ${badge(getPriorityMeta(selectedPlan.priority).label, getPriorityMeta(selectedPlan.priority).tone)}
        </div>
        <div class="detail-grid">
          <div class="detail-box">
            <div class="detail-label">时间周期</div>
            <div class="detail-value">${escapeHtml(formatDisplayDate(selectedPlan.startDate))}</div>
            <div class="detail-subvalue">${escapeHtml(formatDisplayDate(selectedPlan.endDate))}</div>
          </div>
          <div class="detail-box">
            <div class="detail-label">状态与归属</div>
            <div class="detail-value">${escapeHtml(selectedPlan.status)}</div>
            <div class="detail-subvalue">${escapeHtml(displayText(selectedPlan.project))} · ${escapeHtml(displayText(selectedPlan.category))} · ${escapeHtml(displayText(selectedPlan.owner, "未设置负责人"))}</div>
          </div>
        </div>
        <div class="detail-grid progress-grid">
          <div class="detail-box">
            <div class="detail-label">项目进度</div>
            <div class="detail-value">${projectProgress}%</div>
            <div class="detail-subvalue">项目下所有计划平均值</div>
          </div>
          <div class="detail-box">
            <div class="detail-label">工作分类进度</div>
            <div class="detail-value">${categoryProgress}%</div>
            <div class="detail-subvalue">该工作分类下所有计划平均值</div>
          </div>
        </div>
        <div class="plan-progress">
          <div class="plan-progress-row">
            <span>计划进度</span>
            <span>${planProgress}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" style="width:${planProgress}%"></div>
          </div>
        </div>
        <div class="detail-box">
          <div class="detail-label">进度标准</div>
          <div class="detail-copy">有关键节点时：按已完成节点数 / 总节点数计算。没有关键节点时：未开始 0%，进行中 50%，阻塞 25%，已完成 100%。项目和工作分类进度按其下计划平均值计算。</div>
        </div>
        <div class="detail-box">
          <div class="detail-label">下一步动作</div>
          <div class="detail-copy">${escapeHtml(selectedPlan.nextAction || "未填写")}</div>
        </div>
        <div class="detail-box">
          <div class="detail-label">成功标准</div>
          <div class="detail-copy">${escapeHtml(selectedPlan.successMetric || "未填写")}</div>
        </div>
        <div class="detail-box">
          <div class="detail-label">备注</div>
          <div class="detail-copy">${escapeHtml(selectedPlan.notes || "未填写")}</div>
        </div>
        <div class="detail-actions">
          <button type="button" class="button-primary" data-action="edit-plan" data-plan-id="${selectedPlan.id}">编辑计划</button>
          <button type="button" class="button-ghost" data-action="delete-plan" data-plan-id="${selectedPlan.id}">删除计划</button>
        </div>
      </div>

      <div class="surface">
        <div class="section-head">
          <div>
            <div class="section-kicker">Milestones</div>
            <h3 class="subsection-title">关键节点</h3>
          </div>
          <button type="button" class="button-primary" data-action="open-milestone-create" data-plan-id="${selectedPlan.id}">新增节点</button>
        </div>
        ${
          selectedPlan.milestones.length
            ? `<div class="milestone-list">
                ${selectedPlan.milestones
                  .map((item) => `
                    <div class="milestone-card">
                      <div class="milestone-row">
                        <input type="checkbox" ${item.done ? "checked" : ""} data-action="toggle-milestone" data-plan-id="${selectedPlan.id}" data-milestone-id="${item.id}" />
                        ${milestoneIcon(item.icon)}
                        <div style="flex:1;">
                          <div class="milestone-title">${escapeHtml(item.title)}</div>
                          <div class="milestone-meta">${item.dueDate ? escapeHtml(formatDisplayDate(item.dueDate)) : "未设置日期"}</div>
                        </div>
                        ${badge(item.done ? "完成" : weekLabel(item.dueDate || selectedPlan.endDate), item.done ? "success" : daysLeft(item.dueDate || selectedPlan.endDate) < 0 ? "danger" : "muted")}
                        <button type="button" class="button-ghost" data-action="edit-milestone" data-plan-id="${selectedPlan.id}" data-milestone-id="${item.id}">编辑</button>
                        <button type="button" class="button-ghost danger-ghost" data-action="delete-milestone" data-plan-id="${selectedPlan.id}" data-milestone-id="${item.id}">删除</button>
                      </div>
                    </div>
                  `)
                  .join("")}
              </div>`
            : `<div class="empty-state">还没有定义里程碑。可以单独新增、编辑和删除关键节点。</div>`
        }
      </div>

      <div class="surface">
        <div class="section-head">
          <div>
            <div class="section-kicker">Updates</div>
            <h3 class="subsection-title">推进记录</h3>
          </div>
        </div>
        <textarea id="update-text" class="field-control textarea-control" placeholder="记录今天的推进情况、问题或决策。"></textarea>
        <div class="detail-actions" style="margin-top:12px;">
          <span></span>
          <button type="button" class="button-primary" data-action="add-update" data-plan-id="${selectedPlan.id}">添加更新</button>
        </div>
        ${
          selectedPlan.updates.length
            ? `<div class="update-list">
                ${selectedPlan.updates
                  .map(
                    (item) => `
                      <div class="update-card">
                        <div class="update-date">${escapeHtml(formatDisplayDate(item.date))}</div>
                        <div class="detail-copy">${escapeHtml(item.text)}</div>
                      </div>
                    `,
                  )
                  .join("")}
              </div>`
            : `<div class="empty-state" style="margin-top:14px;">还没有推进记录。</div>`
        }
      </div>
    </div>
  `;
}

function renderDetail(selectedPlan) {
  if (state.selectedPlanId && selectedPlan) {
    return renderPlanDetail(selectedPlan);
  }
  if (state.selectedCategoryKey) {
    const [projectName, categoryName] = state.selectedCategoryKey.split("::");
    return renderCategoryDetail(projectName, categoryName);
  }
  if (state.selectedProjectName) {
    return renderProjectDetail(state.selectedProjectName);
  }
  return "";
}

function renderTimeline(filteredPlans) {
  const bounds = getTimelineBounds(filteredPlans);
  const timeline = createDateRange(bounds.start, bounds.end);
  const todayString = formatDate(new Date());
  const timelineDayWidth = TIMELINE_ZOOM_LEVELS[state.timelineZoom] || TIMELINE_ZOOM_LEVELS[1];
  const timelineScale = Number((timelineDayWidth / 64).toFixed(2));
  const timelineDayColumns = `repeat(${timeline.length}, minmax(${timelineDayWidth}px, ${timelineDayWidth}px))`;
  const timelineLabelColumns = `minmax(0, 1.8fr) 112px 88px`;
  const timelineLayoutColumns = `420px minmax(max-content, 1fr)`;

  const renderLabelGrid = (title, meta, progressText, extraClass = "", indentClass = "", prefix = "") => `
    <div class="timeline-grid-label ${extraClass}">
      <div class="timeline-grid-cell timeline-grid-name ${indentClass}">
        <div class="timeline-gantt-title">${prefix}${escapeHtml(title)}</div>
      </div>
      <div class="timeline-grid-cell">
        <div class="timeline-gantt-meta timeline-grid-meta">${escapeHtml(meta)}</div>
      </div>
      <div class="timeline-grid-cell timeline-grid-progress">${escapeHtml(progressText)}</div>
    </div>
  `;

  const renderPlanRow = (plan) => {
    const colorMeta = getColorMeta(plan.markColor);
    const startOffset = diffDays(plan.startDate, timeline[0]);
    const span = diffDays(plan.endDate, plan.startDate) + 1;
    const planProgress = getPlanProgress(plan);
    return `
      <div class="timeline-gantt-row timeline-gantt-row-plan" style="grid-template-columns: ${timelineLayoutColumns};">
        <div class="timeline-gantt-label timeline-sticky timeline-gantt-label-plan timeline-draggable" draggable="true" data-drag-type="plan" data-plan-id="${plan.id}">
          ${renderLabelGrid(plan.title, plan.status, `${planProgress}%`, "", "is-plan", `<span class="drag-handle">⋮⋮</span>`)}
        </div>
        <div class="timeline-gantt-track" style="grid-template-columns: ${timelineDayColumns};">
          <div class="timeline-gantt-bar color-${colorMeta.value}" style="grid-column: ${startOffset + 1} / span ${span};">
            <span>${escapeHtml(plan.title)}</span>
            <strong>${planProgress}%</strong>
          </div>
          ${plan.milestones
            .filter((item) => item.dueDate)
            .map((item) => {
              const offset = diffDays(item.dueDate, timeline[0]);
              return `<div class="timeline-gantt-milestone ${item.done ? "done" : ""}" style="grid-column:${offset + 1};" title="${escapeHtml(item.title)}">${getIconMeta(item.icon).symbol}</div>`;
            })
            .join("")}
        </div>
      </div>
    `;
  };

  const renderCategoryRows = (projectName, categoryName, categoryPlans) => {
    const category = getCategoryRecord(projectName, categoryName);
    const categoryKey = getCategoryKey(projectName, categoryName);
    const categoryExpanded = state.expandedCategoryKeys.includes(categoryKey);
    const categoryStart = categoryPlans.reduce((min, plan) => (parseDate(plan.startDate) < parseDate(min) ? plan.startDate : min), categoryPlans[0].startDate);
    const categoryEnd = categoryPlans.reduce((max, plan) => (parseDate(plan.endDate) > parseDate(max) ? plan.endDate : max), categoryPlans[0].endDate);
    const startOffset = diffDays(categoryStart, timeline[0]);
    const span = diffDays(categoryEnd, categoryStart) + 1;
    const categoryProgress = getCategoryProgress(projectName, categoryName);
    return `
      <div class="timeline-gantt-row timeline-gantt-row-category" style="grid-template-columns: ${timelineLayoutColumns};">
        <div class="timeline-gantt-label timeline-sticky timeline-gantt-label-category timeline-draggable" ${category ? `draggable="true" data-drag-type="category" data-category-id="${category.id}"` : ""}>
          ${renderLabelGrid(categoryName, `${categoryPlans.length} 条计划`, `${categoryProgress}%`, "", "is-category", `<button type="button" class="timeline-fold-toggle" data-action="timeline-toggle-category" data-project-name="${escapeHtml(projectName)}" data-category-name="${escapeHtml(categoryName)}">${categoryExpanded ? "▾" : "▸"}</button><span class="drag-handle">⋮⋮</span>`)}
        </div>
        <div class="timeline-gantt-track timeline-gantt-track-category" style="grid-template-columns: ${timelineDayColumns};">
          <div class="timeline-gantt-bar timeline-gantt-bar-category" style="grid-column: ${startOffset + 1} / span ${span};">
            <span>${escapeHtml(categoryName)}</span>
            <strong>${categoryProgress}%</strong>
          </div>
        </div>
      </div>
      ${categoryExpanded ? categoryPlans.map((plan) => renderPlanRow(plan)).join("") : ""}
    `;
  };

  return `
    <section id="timeline" class="surface timeline timeline-zoom-${state.timelineZoom}" style="--timeline-day-width:${timelineDayWidth}px; --timeline-scale:${timelineScale};">
      <div class="section-head">
        <div>
          <div class="section-kicker">Timeline</div>
          <h2 class="section-title">时间轴</h2>
          <div class="muted" style="margin-top:6px;">周序按全年 ISO 周显示，例如 2026-03-22 对应 W12。</div>
        </div>
        <div class="timeline-actions">
          <button type="button" class="button-ghost" data-action="timeline-prev">查看更早</button>
          <button type="button" class="button-ghost" data-action="timeline-today">返回今日</button>
          <button type="button" class="button-ghost" data-action="timeline-calendar">查看日历</button>
          <button type="button" class="button-ghost" data-action="timeline-next">查看更晚</button>
        </div>
        <div class="timeline-controls">
          <div class="timeline-zoom-group">
            <button type="button" class="button-ghost" data-action="timeline-zoom-out" ${state.timelineZoom === 0 ? "disabled" : ""}>缩小</button>
            <div class="timeline-zoom-label">缩放 ${state.timelineZoom + 1}/${TIMELINE_ZOOM_LEVELS.length}</div>
            <button type="button" class="button-ghost" data-action="timeline-zoom-in" ${state.timelineZoom === TIMELINE_ZOOM_LEVELS.length - 1 ? "disabled" : ""}>放大</button>
          </div>
          <input id="timeline-slider" class="timeline-slider" type="range" min="0" max="100" value="0" />
          <input id="timeline-date-picker" class="timeline-date-picker" type="date" value="${todayString}" />
        </div>
      </div>
      <div id="timeline-scroll" class="timeline-scroll">
        <div class="timeline-board">
          <div class="timeline-header-shell" style="grid-template-columns: ${timelineLayoutColumns};">
            <div class="timeline-corner timeline-sticky">
              <div class="timeline-grid-label timeline-grid-head" style="grid-template-columns:${timelineLabelColumns};">
                <div class="timeline-grid-cell">项目分类计划</div>
                <div class="timeline-grid-cell">状态</div>
                <div class="timeline-grid-cell">进度</div>
              </div>
              <div class="timeline-head-actions">
                <button type="button" class="button-ghost timeline-head-button" data-action="timeline-expand-all">全部展开</button>
              </div>
            </div>
            <div class="timeline-header-grid" style="grid-template-columns: ${timelineDayColumns};">
              ${timeline
                .map(
                  (date) => `
                    <div class="timeline-date ${formatDate(date) === todayString ? "timeline-today-cell" : ""}" data-date="${formatDate(date)}">
                      <div>${escapeHtml(weekLabel(formatDate(date)))}</div>
                      <div>${escapeHtml(formatShortDate(formatDate(date)))}</div>
                      <div>${escapeHtml(weekdayLabel(formatDate(date)))}</div>
                    </div>
                  `,
                )
                .join("")}
            </div>
          </div>
          ${Array.from(new Set(filteredPlans.map((plan) => plan.project).filter(Boolean)))
            .map((projectName) => {
              const projectPlans = filteredPlans.filter((plan) => plan.project === projectName);
              const projectExpanded = state.expandedProjects.includes(projectName);
              const projectStart = projectPlans.reduce((min, plan) => (parseDate(plan.startDate) < parseDate(min) ? plan.startDate : min), projectPlans[0].startDate);
              const projectEnd = projectPlans.reduce((max, plan) => (parseDate(plan.endDate) > parseDate(max) ? plan.endDate : max), projectPlans[0].endDate);
              const projectStartOffset = diffDays(projectStart, timeline[0]);
              const projectSpan = diffDays(projectEnd, projectStart) + 1;
              const projectCategories = getCategoriesForProject(projectName)
                .map((item) => item.name)
                .filter((name) => projectPlans.some((plan) => plan.category === name));
              return `
                <div class="timeline-project-shell">
                  <div class="timeline-project-head" style="grid-template-columns: ${timelineLayoutColumns};">
                    <div class="timeline-project-panel timeline-sticky">
                      ${renderLabelGrid(projectName, `${projectCategories.length} 个分类`, `${getProjectProgress(projectName)}%`, "timeline-grid-project", "is-project", `<button type="button" class="timeline-fold-toggle" data-action="timeline-toggle-project" data-project-name="${escapeHtml(projectName)}">${projectExpanded ? "▾" : "▸"}</button>`)}
                    </div>
                    <div class="timeline-project-divider timeline-gantt-track" style="grid-template-columns: ${timelineDayColumns};">
                      <div class="timeline-gantt-bar timeline-gantt-bar-project" style="grid-column: ${projectStartOffset + 1} / span ${projectSpan};">
                        <span>${escapeHtml(projectName)}</span>
                        <strong>${getProjectProgress(projectName)}%</strong>
                      </div>
                    </div>
                  </div>
                  ${projectExpanded
                    ? projectCategories
                        .map((categoryName) => {
                          const categoryPlans = projectPlans.filter((plan) => plan.category === categoryName).sort((a, b) => a.order - b.order || a.title.localeCompare(b.title, "zh-CN"));
                          return renderCategoryRows(projectName, categoryName, categoryPlans);
                        })
                        .join("")
                    : ""}
                </div>
              `;
            })
            .join("")}
        </div>
      </div>
    </section>
  `;
}

function renderComposer() {
  if (!state.composerOpen) return "";
  if (state.composerMode === "project") {
    const editingProjectName = state.editingProjectName || "";
    return `
      <div class="modal-backdrop" id="composer-backdrop">
        <div class="modal modal-small">
          <div class="modal-header">
            <div>
              <div class="field-label">Project</div>
              <div class="section-title">${editingProjectName ? "编辑项目" : "新建项目"}</div>
            </div>
            <button type="button" class="button-ghost" data-action="close-composer">关闭</button>
          </div>
          <div class="modal-body">
            <form id="project-form" class="form-grid">
              <input type="hidden" name="originalProjectName" value="${escapeHtml(editingProjectName)}" />
              <label class="field">
                <span class="field-label">项目名称</span>
                <input id="project-name-input" class="field-control" name="projectName" value="${escapeHtml(editingProjectName)}" required />
              </label>
              <div class="detail-actions">
                <span></span>
                <button type="submit" class="button-primary">保存项目</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `;
  }
  if (state.composerMode === "category") {
    const editingCategory = state.editingCategoryId ? getCategoryById(state.editingCategoryId) : null;
    return `
      <div class="modal-backdrop" id="composer-backdrop">
        <div class="modal modal-small">
          <div class="modal-header">
            <div>
              <div class="field-label">Category</div>
              <div class="section-title">${editingCategory ? "编辑工作分类" : "新建工作分类"}</div>
            </div>
            <button type="button" class="button-ghost" data-action="close-composer">关闭</button>
          </div>
          <div class="modal-body">
            <form id="category-form" class="form-grid">
              <input type="hidden" name="categoryId" value="${escapeHtml(editingCategory ? editingCategory.id : "")}" />
              <label class="field">
                <span class="field-label">所属项目</span>
                <select id="category-project-input" class="field-control" name="projectName" required>
                  <option value="">请选择项目</option>
                  ${state.data.projects.map((item) => `<option value="${escapeHtml(item)}" ${editingCategory && item === editingCategory.project ? "selected" : ""}>${escapeHtml(item)}</option>`).join("")}
                </select>
              </label>
              <label class="field">
                <span class="field-label">工作分类名称</span>
                <input id="category-name-input" class="field-control" name="categoryName" value="${escapeHtml(editingCategory ? editingCategory.name : "")}" required />
              </label>
              <div class="detail-actions">
                <span></span>
                <button type="submit" class="button-primary">保存分类</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `;
  }
  if (state.composerMode === "milestone") {
    const plan = state.data.plans.find((item) => item.id === state.milestonePlanId);
    const existing = plan ? plan.milestones.find((item) => item.id === state.editingMilestoneId) : null;
    const milestone = sanitizeMilestone(existing || {});
    return `
      <div class="modal-backdrop" id="composer-backdrop">
        <div class="modal modal-small">
          <div class="modal-header">
            <div>
              <div class="field-label">Milestone</div>
              <div class="section-title">${existing ? "编辑关键节点" : "新增关键节点"}</div>
            </div>
            <button type="button" class="button-ghost" data-action="close-composer">关闭</button>
          </div>
          <div class="modal-body">
            <form id="milestone-form" class="form-grid">
              <input type="hidden" name="id" value="${escapeHtml(milestone.id)}" />
              <label class="field">
                <span class="field-label">节点标题</span>
                <input class="field-control" name="title" value="${escapeHtml(existing ? existing.title : "")}" required />
              </label>
              <label class="field">
                <span class="field-label">节点日期</span>
                <input class="field-control" type="date" name="dueDate" value="${escapeHtml(existing ? existing.dueDate : "")}" />
              </label>
              <label class="field">
                <span class="field-label">节点图标</span>
                <select class="field-control" name="icon">
                  ${MILESTONE_ICONS.map((item) => `<option value="${item.value}" ${item.value === milestone.icon ? "selected" : ""}>${item.symbol} ${escapeHtml(item.label)}</option>`).join("")}
                </select>
              </label>
              <label class="field">
                <span class="field-label">是否完成</span>
                <select class="field-control" name="done">
                  <option value="false" ${!milestone.done ? "selected" : ""}>未完成</option>
                  <option value="true" ${milestone.done ? "selected" : ""}>已完成</option>
                </select>
              </label>
              <div class="detail-actions">
                <span></span>
                <button type="submit" class="button-primary">保存节点</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `;
  }
  const editingPlan = getCurrentEditingPlan();
  const plan = sanitizePlan(
    editingPlan || {
      title: "",
      project: "",
      category: "",
      startDate: formatDate(new Date()),
      endDate: formatDate(new Date()),
      owner: "",
      updates: [],
      markColor: "yellow",
    },
  );

  return `
    <div class="modal-backdrop" id="composer-backdrop">
      <div class="modal">
        <div class="modal-header">
          <div>
            <div class="field-label">Plan Editor</div>
            <div class="section-title">${editingPlan ? "编辑计划" : "新建计划"}</div>
          </div>
          <button type="button" class="button-ghost" data-action="close-composer">关闭</button>
        </div>
        <div class="modal-body">
          <form id="plan-form" class="form-grid">
            <input type="hidden" name="id" value="${escapeHtml(plan.id)}" />
            <div class="form-grid cols-4">
              <label class="field span-2">
                <span class="field-label">计划主题</span>
                <input class="field-control" name="title" value="${escapeHtml(plan.title === "未命名计划" ? "" : plan.title)}" required />
              </label>
              <label class="field">
                <span class="field-label">负责人</span>
                <input class="field-control" name="owner" value="${escapeHtml(plan.owner)}" />
              </label>
              <div></div>
            </div>

            <div class="form-grid cols-4">
              <label class="field">
                <span class="field-label">所属项目</span>
                <select id="plan-project-select" class="field-control" name="project">
                  <option value="">未设置</option>
                  ${state.data.projects.map((item) => `<option value="${escapeHtml(item)}" ${item === plan.project ? "selected" : ""}>${escapeHtml(item)}</option>`).join("")}
                </select>
              </label>
              <label class="field">
                <span class="field-label">工作分类</span>
                <select id="plan-category-select" class="field-control" name="categoryId">
                  <option value="">未设置</option>
                  ${renderCategoryOptions(plan.project, plan.category)}
                </select>
              </label>
              <label class="field">
                <span class="field-label">颜色标注</span>
                <select class="field-control" name="markColor">
                  ${COLOR_OPTIONS.map((item) => `<option value="${item.value}" ${item.value === plan.markColor ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("")}
                </select>
              </label>
              <label class="field">
                <span class="field-label">优先级</span>
                <select class="field-control" name="priority">
                  ${PRIORITY_OPTIONS.map((item) => `<option value="${escapeHtml(item)}" ${item === plan.priority ? "selected" : ""}>${escapeHtml(item)}</option>`).join("")}
                </select>
              </label>
            </div>

            <div class="form-grid cols-4">
              <label class="field">
                <span class="field-label">执行状态</span>
                <select class="field-control" name="status">
                  ${STATUS_OPTIONS.map((item) => `<option value="${escapeHtml(item)}" ${item === plan.status ? "selected" : ""}>${escapeHtml(item)}</option>`).join("")}
                </select>
              </label>
              <label class="field">
                <span class="field-label">开始日期</span>
                <input class="field-control" type="date" name="startDate" value="${escapeHtml(plan.startDate)}" />
              </label>
              <label class="field">
                <span class="field-label">结束日期</span>
                <input class="field-control" type="date" name="endDate" value="${escapeHtml(plan.endDate)}" />
              </label>
              <label class="field">
                <span class="field-label">推进节奏</span>
                <select class="field-control" name="cadence">
                  ${CADENCE_OPTIONS.map((item) => `<option value="${escapeHtml(item)}" ${item === plan.cadence ? "selected" : ""}>${escapeHtml(item)}</option>`).join("")}
                </select>
              </label>
            </div>

            <div class="form-grid cols-2">
              <label class="field">
                <span class="field-label">下一步动作</span>
                <textarea class="field-control textarea-control" name="nextAction">${escapeHtml(plan.nextAction)}</textarea>
              </label>
              <label class="field">
                <span class="field-label">成功标准</span>
                <textarea class="field-control textarea-control" name="successMetric">${escapeHtml(plan.successMetric)}</textarea>
              </label>
            </div>

            <label class="field">
              <span class="field-label">备注</span>
              <textarea class="field-control textarea-control" name="notes">${escapeHtml(plan.notes)}</textarea>
            </label>
            <div class="detail-actions">
              <span></span>
              <button type="submit" class="button-primary">保存计划</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;
}

function renderLoading() {
  document.getElementById("app").innerHTML = `
    <div class="page-shell">
      <div class="surface loading-shell">正在连接数据库并加载计划数据...</div>
    </div>
  `;
}

function render() {
  if (!state.loaded) {
    renderLoading();
    return;
  }

  const filteredPlans = getFilteredPlans();
  const selectedPlan = getSelectedPlan(filteredPlans);
  if (selectedPlan) state.selectedPlanId = selectedPlan.id;
  const metrics = getMetrics(filteredPlans);

  document.getElementById("app").innerHTML = `
    <header class="topbar">
        <div class="topbar-inner">
        <div class="brand">
          <div>
            <div class="brand-name">工作计划管理</div>
            <div class="brand-subtitle">本地数据库已连接 · 版本 ${APP_VERSION}</div>
          </div>
        </div>
        <div class="topbar-actions">
          <button type="button" class="button-ghost" data-action="open-project-create">新建项目</button>
          <button type="button" class="button-ghost" data-action="open-category-create">新建工作分类</button>
          <a class="button-ghost" href="#timeline">时间轴</a>
          <button type="button" class="button-ghost danger-ghost" data-action="shutdown-app">退出</button>
          <button type="button" class="button-primary" data-action="open-create">新建计划</button>
        </div>
      </div>
    </header>
    <div class="page-shell">
      ${renderStats(metrics)}
      ${renderWorkspace(filteredPlans, selectedPlan)}
      ${renderTimeline(filteredPlans)}
      ${renderComposer()}
    </div>
  `;

  bindEvents();
}

function bindEvents() {
  document.querySelectorAll("[data-action='open-create']").forEach((button) => {
    button.addEventListener("click", () => openComposer(null));
  });
  document.querySelectorAll("[data-action='open-project-create']").forEach((button) => {
    button.addEventListener("click", openProjectComposer);
  });
  document.querySelectorAll("[data-action='open-category-create']").forEach((button) => {
    button.addEventListener("click", openCategoryComposer);
  });
  document.querySelectorAll("[data-action='shutdown-app']").forEach((button) => {
    button.addEventListener("click", () => {
      if (window.confirm("确认退出并关闭本地服务吗？")) shutdownApp();
    });
  });
  document.querySelectorAll("[data-action='close-composer']").forEach((button) => {
    button.addEventListener("click", closeComposer);
  });
  const backdrop = document.getElementById("composer-backdrop");
  if (backdrop) {
    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) closeComposer();
    });
  }

  const search = document.getElementById("search-input");
  if (search) search.addEventListener("input", (event) => { state.filters.search = event.target.value; render(); });
  const project = document.getElementById("project-filter");
  if (project) project.addEventListener("change", (event) => {
    state.filters.project = event.target.value;
    state.filters.category = "全部分类";
    render();
  });
  const category = document.getElementById("category-filter");
  if (category) category.addEventListener("change", (event) => { state.filters.category = event.target.value; render(); });
  const status = document.getElementById("status-filter");
  if (status) status.addEventListener("change", (event) => { state.filters.status = event.target.value; render(); });

  document.querySelectorAll("[data-action='select-plan']").forEach((button) => {
    button.addEventListener("click", () => {
      const planId = button.getAttribute("data-plan-id");
      const plan = state.data.plans.find((item) => item.id === planId);
      state.selectedPlanId = planId;
      state.selectedProjectName = plan ? plan.project : "";
      state.selectedCategoryKey = plan ? getCategoryKey(plan.project, plan.category) : "";
      render();
    });
  });

  document.querySelectorAll("[data-action='select-project-node']").forEach((button) => {
    button.addEventListener("click", () => {
      const projectName = button.getAttribute("data-project-name");
      state.selectedProjectName = projectName;
      state.selectedCategoryKey = "";
      state.selectedPlanId = "";
      toggleExpandedProject(projectName);
      render();
    });
  });

  document.querySelectorAll("[data-action='select-category-node']").forEach((button) => {
    button.addEventListener("click", () => {
      const projectName = button.getAttribute("data-project-name");
      const categoryName = button.getAttribute("data-category-name");
      state.selectedProjectName = projectName;
      state.selectedCategoryKey = getCategoryKey(projectName, categoryName);
      state.selectedPlanId = "";
      if (!state.expandedProjects.includes(projectName)) {
        state.expandedProjects = [...state.expandedProjects, projectName];
      }
      toggleExpandedCategory(projectName, categoryName);
      render();
    });
  });

  document.querySelectorAll("[data-action='timeline-toggle-project']").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const projectName = button.getAttribute("data-project-name");
      if (!projectName) return;
      toggleExpandedProject(projectName);
      render();
    });
  });

  document.querySelectorAll("[data-action='timeline-toggle-category']").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const projectName = button.getAttribute("data-project-name");
      const categoryName = button.getAttribute("data-category-name");
      if (!projectName || !categoryName) return;
      if (!state.expandedProjects.includes(projectName)) {
        state.expandedProjects = [...state.expandedProjects, projectName];
      }
      toggleExpandedCategory(projectName, categoryName);
      render();
    });
  });

  document.querySelectorAll("[data-action='timeline-expand-all']").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const filteredPlans = getFilteredPlans();
      const projectNames = Array.from(new Set(filteredPlans.map((plan) => plan.project).filter(Boolean)));
      state.expandedProjects = projectNames;
      state.expandedCategoryKeys = Array.from(
        new Set(
          filteredPlans
            .filter((plan) => plan.project && plan.category)
            .map((plan) => getCategoryKey(plan.project, plan.category)),
        ),
      );
      render();
    });
  });

  document.querySelectorAll(".timeline-draggable").forEach((element) => {
    element.addEventListener("dragstart", (event) => {
      const dragType = element.getAttribute("data-drag-type");
      const categoryId = element.getAttribute("data-category-id");
      const planId = element.getAttribute("data-plan-id");
      if (!event.dataTransfer || !dragType) return;
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", JSON.stringify({ dragType, categoryId, planId }));
      element.classList.add("is-dragging");
    });
    element.addEventListener("dragend", () => {
      element.classList.remove("is-dragging");
      document.querySelectorAll(".timeline-draggable.is-drop-target").forEach((item) => item.classList.remove("is-drop-target"));
    });
    element.addEventListener("dragover", (event) => {
      if (!event.dataTransfer) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      element.classList.add("is-drop-target");
    });
    element.addEventListener("dragleave", () => {
      element.classList.remove("is-drop-target");
    });
    element.addEventListener("drop", (event) => {
      event.preventDefault();
      element.classList.remove("is-drop-target");
      if (!event.dataTransfer) return;
      let payload;
      try {
        payload = JSON.parse(event.dataTransfer.getData("text/plain"));
      } catch {
        payload = null;
      }
      if (!payload || payload.dragType !== element.getAttribute("data-drag-type")) return;
      if (payload.dragType === "category") {
        moveCategory(payload.categoryId, element.getAttribute("data-category-id"));
      }
      if (payload.dragType === "plan") {
        movePlan(payload.planId, element.getAttribute("data-plan-id"));
      }
    });
  });

  const timelineScroll = document.getElementById("timeline-scroll");
  const timelineSlider = document.getElementById("timeline-slider");
  const timelineDatePicker = document.getElementById("timeline-date-picker");
  const timelineHeaderGrid = document.querySelector(".timeline-header-grid");
  const timelinePinnedCell = document.querySelector(".timeline-corner");
  const updateTimelineSlider = () => {
    if (!timelineScroll || !timelineSlider) return;
    const maxScroll = Math.max(0, timelineScroll.scrollWidth - timelineScroll.clientWidth);
    timelineSlider.disabled = maxScroll === 0;
    timelineSlider.value = maxScroll ? String(Math.round((timelineScroll.scrollLeft / maxScroll) * 100)) : "0";
  };
  const scrollTimelineToRatio = (ratio) => {
    if (!timelineScroll || !timelineSlider) return;
    const maxScroll = Math.max(0, timelineScroll.scrollWidth - timelineScroll.clientWidth);
    timelineScroll.scrollLeft = maxScroll * ratio;
  };
  const scrollTimelineToDate = (dateValue, behavior = "smooth") => {
    if (!timelineScroll || !timelineHeaderGrid) return;
    const targetCell = timelineHeaderGrid.querySelector(`[data-date="${dateValue}"]`);
    if (!targetCell) return;
    const pinnedWidth = timelinePinnedCell ? timelinePinnedCell.offsetWidth : 0;
    const targetLeft = timelineHeaderGrid.offsetLeft + targetCell.offsetLeft - pinnedWidth - 14;
    timelineScroll.scrollTo({ left: Math.max(0, targetLeft), behavior });
  };
  if (timelineScroll && timelineSlider) {
    requestAnimationFrame(updateTimelineSlider);
    window.addEventListener("resize", updateTimelineSlider);
    timelineScroll.addEventListener("scroll", updateTimelineSlider);
    timelineSlider.addEventListener("input", () => {
      scrollTimelineToRatio(Number(timelineSlider.value) / 100);
    });
  }
  if (timelineDatePicker) {
    timelineDatePicker.value = state.timelineAnchorDate || formatDate(new Date());
  }
  if (timelineScroll && timelineHeaderGrid && state.timelineAnchorDate) {
    requestAnimationFrame(() => {
      scrollTimelineToDate(state.timelineAnchorDate, "auto");
      updateTimelineSlider();
    });
  }
  document.querySelectorAll("[data-action='timeline-prev']").forEach((button) => {
    button.addEventListener("click", () => {
      if (timelineScroll) timelineScroll.scrollBy({ left: -420, behavior: "smooth" });
    });
  });
  document.querySelectorAll("[data-action='timeline-next']").forEach((button) => {
    button.addEventListener("click", () => {
      if (timelineScroll) timelineScroll.scrollBy({ left: 420, behavior: "smooth" });
    });
  });
  document.querySelectorAll("[data-action='timeline-today']").forEach((button) => {
    button.addEventListener("click", () => {
      if (!timelineScroll) return;
      const todayValue = formatDate(new Date());
      state.timelineAnchorDate = todayValue;
      if (!timelineHeaderGrid || !timelineHeaderGrid.querySelector(`[data-date="${todayValue}"]`)) {
        timelineScroll.scrollTo({ left: 0, behavior: "smooth" });
        return;
      }
      scrollTimelineToDate(todayValue);
    });
  });
  document.querySelectorAll("[data-action='timeline-calendar']").forEach((button) => {
    button.addEventListener("click", () => {
      if (!timelineDatePicker) return;
      if (typeof timelineDatePicker.showPicker === "function") {
        timelineDatePicker.showPicker();
      } else {
        timelineDatePicker.click();
      }
    });
  });
  if (timelineDatePicker && timelineScroll) {
    timelineDatePicker.addEventListener("change", () => {
      state.timelineAnchorDate = timelineDatePicker.value;
      scrollTimelineToDate(timelineDatePicker.value);
    });
  }
  document.querySelectorAll("[data-action='timeline-zoom-out']").forEach((button) => {
    button.addEventListener("click", () => {
      state.timelineAnchorDate = (document.getElementById("timeline-date-picker") && document.getElementById("timeline-date-picker").value) || state.timelineAnchorDate || formatDate(new Date());
      state.timelineZoom = clamp(state.timelineZoom - 1, 0, TIMELINE_ZOOM_LEVELS.length - 1);
      render();
    });
  });
  document.querySelectorAll("[data-action='timeline-zoom-in']").forEach((button) => {
    button.addEventListener("click", () => {
      state.timelineAnchorDate = (document.getElementById("timeline-date-picker") && document.getElementById("timeline-date-picker").value) || state.timelineAnchorDate || formatDate(new Date());
      state.timelineZoom = clamp(state.timelineZoom + 1, 0, TIMELINE_ZOOM_LEVELS.length - 1);
      render();
    });
  });

  document.querySelectorAll("[data-action='edit-plan']").forEach((button) => {
    button.addEventListener("click", () => openComposer(button.getAttribute("data-plan-id")));
  });

  document.querySelectorAll("[data-action='edit-project']").forEach((button) => {
    button.addEventListener("click", () => openProjectEditor(button.getAttribute("data-project-name")));
  });

  document.querySelectorAll("[data-action='edit-category']").forEach((button) => {
    button.addEventListener("click", () => openCategoryEditor(button.getAttribute("data-category-id")));
  });

  document.querySelectorAll("[data-action='delete-plan']").forEach((button) => {
    button.addEventListener("click", () => {
      const planId = button.getAttribute("data-plan-id");
      const target = state.data.plans.find((plan) => plan.id === planId);
      if (window.confirm(`确认删除计划「${target ? target.title : ""}」吗？`)) deletePlan(planId);
    });
  });

  document.querySelectorAll("[data-action='delete-project']").forEach((button) => {
    button.addEventListener("click", () => {
      const projectName = button.getAttribute("data-project-name");
      const categoryCount = state.data.categories.filter((item) => item.project === projectName).length;
      const planCount = state.data.plans.filter((plan) => plan.project === projectName).length;
      const confirmed = window.confirm(`删除项目「${projectName}」后，会同时删除 ${categoryCount} 个工作分类和 ${planCount} 条计划。确认继续吗？`);
      if (confirmed) deleteProject(projectName);
    });
  });

  document.querySelectorAll("[data-action='delete-category']").forEach((button) => {
    button.addEventListener("click", () => {
      const categoryId = button.getAttribute("data-category-id");
      const category = getCategoryById(categoryId);
      if (!category) return;
      const planCount = state.data.plans.filter((plan) => plan.project === category.project && plan.category === category.name).length;
      const confirmed = window.confirm(`删除工作分类「${category.name}」后，会同时删除该分类下的 ${planCount} 条计划。确认继续吗？`);
      if (confirmed) deleteCategory(categoryId);
    });
  });

  document.querySelectorAll("[data-action='toggle-milestone']").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      toggleMilestone(checkbox.getAttribute("data-plan-id"), checkbox.getAttribute("data-milestone-id"));
    });
  });

  document.querySelectorAll("[data-action='open-milestone-create']").forEach((button) => {
    button.addEventListener("click", () => openMilestoneComposer(button.getAttribute("data-plan-id")));
  });

  document.querySelectorAll("[data-action='edit-milestone']").forEach((button) => {
    button.addEventListener("click", () => openMilestoneComposer(button.getAttribute("data-plan-id"), button.getAttribute("data-milestone-id")));
  });

  document.querySelectorAll("[data-action='delete-milestone']").forEach((button) => {
    button.addEventListener("click", () => {
      const planId = button.getAttribute("data-plan-id");
      const milestoneId = button.getAttribute("data-milestone-id");
      if (window.confirm("确认删除这个关键节点吗？")) deleteMilestone(planId, milestoneId);
    });
  });

  document.querySelectorAll("[data-action='add-update']").forEach((button) => {
    button.addEventListener("click", () => {
      const text = document.getElementById("update-text");
      addUpdate(button.getAttribute("data-plan-id"), text ? text.value : "");
    });
  });

  const form = document.getElementById("plan-form");
  if (form) {
    const projectSelect = document.getElementById("plan-project-select");
    const categorySelect = document.getElementById("plan-category-select");
    if (projectSelect && categorySelect) {
      projectSelect.addEventListener("change", (event) => {
        const projectName = event.target.value;
        categorySelect.innerHTML = `<option value="">未设置</option>${renderCategoryOptions(projectName, "")}`;
      });
    }
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const current = getCurrentEditingPlan();
      const selectedCategory = getCategoryById(formData.get("categoryId"));
      savePlan({
        id: formData.get("id"),
        title: formData.get("title"),
        owner: formData.get("owner"),
        project: formData.get("project"),
        category: selectedCategory ? selectedCategory.name : "",
        priority: formData.get("priority"),
        status: formData.get("status"),
        startDate: formData.get("startDate"),
        endDate: formData.get("endDate"),
        cadence: formData.get("cadence"),
        nextAction: formData.get("nextAction"),
        successMetric: formData.get("successMetric"),
        notes: formData.get("notes"),
        markColor: formData.get("markColor"),
        milestones: current ? current.milestones : [],
        updates: current ? current.updates : [],
      });
    });
  }

  const projectForm = document.getElementById("project-form");
  if (projectForm) {
    projectForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const formData = new FormData(projectForm);
      saveProject(String(formData.get("originalProjectName") || ""), String(formData.get("projectName") || ""));
    });
  }

  const categoryForm = document.getElementById("category-form");
  if (categoryForm) {
    categoryForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const formData = new FormData(categoryForm);
      saveCategory(String(formData.get("categoryId") || ""), String(formData.get("projectName") || ""), String(formData.get("categoryName") || ""));
    });
  }

  const milestoneForm = document.getElementById("milestone-form");
  if (milestoneForm) {
    milestoneForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const formData = new FormData(milestoneForm);
      saveMilestone(state.milestonePlanId, {
        id: formData.get("id"),
        title: formData.get("title"),
        dueDate: formData.get("dueDate"),
        icon: formData.get("icon"),
        done: formData.get("done") === "true",
      });
    });
  }
}

renderLoading();
loadState();
