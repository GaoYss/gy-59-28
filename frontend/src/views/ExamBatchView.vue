<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Plus,
  RefreshCcw,
  Search,
  Trash2,
  TrendingUp,
  Users
} from 'lucide-vue-next'

import { appointmentApi, batchApi } from '../api/modules'
import DataTable from '../components/DataTable.vue'
import EmptyState from '../components/EmptyState.vue'
import MessageBar from '../components/MessageBar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { examBatches } from '../constants/options'

const batches = ref([])
const loading = ref(false)
const saving = ref(false)
const message = reactive({ text: '', type: 'info' })
const expandedRows = ref(new Set())
const filters = reactive({ startDate: '', endDate: '' })

const showCreateForm = ref(false)
const createForm = reactive({ examDate: '', period: examBatches[0], capacity: 30 })

const editingCapacity = ref(null)
const editingValue = ref('')

const detailColumns = [
  { key: 'studentName', label: '学员' },
  { key: 'idNumber', label: '证件号' },
  { key: 'subject', label: '科目' },
  { key: 'timeslot', label: '时段' },
  { key: 'status', label: '状态' }
]

const summary = computed(() => {
  const totalRegistered = batches.value.reduce((sum, b) => sum + b.registered, 0)
  const totalAttended = batches.value.reduce((sum, b) => sum + b.attended, 0)
  const totalCapacity = batches.value.reduce((sum, b) => sum + b.capacity, 0)
  return {
    totalBatches: batches.value.length,
    totalCapacity,
    totalRegistered,
    totalAttended,
    averageRate: totalRegistered > 0 ? Math.round(totalAttended / totalRegistered * 100) : 0
  }
})

function setMessage(text, type = 'info') {
  message.text = text
  message.type = type
}

function toggleExpand(batch) {
  const key = batch.id
  if (expandedRows.value.has(key)) {
    expandedRows.value.delete(key)
  } else {
    expandedRows.value.add(key)
  }
  expandedRows.value = new Set(expandedRows.value)
}

function isExpanded(batch) {
  return expandedRows.value.has(batch.id)
}

function getBatchBadgeClass(period) {
  return period === '上午' ? 'morning' : 'afternoon'
}

async function loadBatches() {
  loading.value = true
  message.text = ''
  try {
    const params = {}
    if (filters.startDate) params.startDate = filters.startDate
    if (filters.endDate) params.endDate = filters.endDate
    batches.value = await batchApi.stats(params)
  } catch (error) {
    setMessage(error.message, 'error')
  } finally {
    loading.value = false
  }
}

async function createBatch() {
  saving.value = true
  setMessage('')
  try {
    await batchApi.create({
      examDate: createForm.examDate,
      period: createForm.period,
      capacity: Number(createForm.capacity)
    })
    createForm.examDate = ''
    createForm.period = examBatches[0]
    createForm.capacity = 30
    showCreateForm.value = false
    setMessage('批次创建成功', 'success')
    await loadBatches()
  } catch (error) {
    setMessage(error.message, 'error')
  } finally {
    saving.value = false
  }
}

async function toggleBatchStatus(batch) {
  const newStatus = batch.status === '开放' ? '关闭' : '开放'
  try {
    await batchApi.update(batch.id, { status: newStatus })
    setMessage(`批次已${newStatus === '开放' ? '开放' : '关闭'}`, 'success')
    await loadBatches()
  } catch (error) {
    setMessage(error.message, 'error')
  }
}

async function deleteBatch(batch) {
  try {
    await batchApi.delete(batch.id)
    setMessage('批次已删除', 'success')
    await loadBatches()
  } catch (error) {
    setMessage(error.message, 'error')
  }
}

function startEditCapacity(batch) {
  editingCapacity.value = batch.id
  editingValue.value = String(batch.capacity)
}

async function saveCapacity(batch) {
  const cap = Number(editingValue.value)
  if (cap < 1) {
    setMessage('容量不能小于1', 'error')
    return
  }
  try {
    await batchApi.update(batch.id, { capacity: cap })
    editingCapacity.value = null
    setMessage('容量已更新', 'success')
    await loadBatches()
  } catch (error) {
    setMessage(error.message, 'error')
  }
}

function cancelEditCapacity() {
  editingCapacity.value = null
  editingValue.value = ''
}

async function markAttended(row) {
  try {
    await appointmentApi.updateStatus(row.id, '已确认')
    await loadBatches()
  } catch (error) {
    setMessage(error.message, 'error')
  }
}

onMounted(loadBatches)
</script>

<template>
  <section class="module-grid two-columns">
    <form class="panel form-panel" @submit.prevent="createBatch">
      <div class="panel-heading">
        <div>
          <h3>新建批次</h3>
          <p>创建上午或下午考试批次，设置容量。</p>
        </div>
        <button
          class="icon-button"
          type="button"
          :title="showCreateForm ? '收起' : '新建'"
          @click="showCreateForm = !showCreateForm"
        >
          <Plus v-if="!showCreateForm" :size="18" />
          <ChevronDown v-else :size="18" />
        </button>
      </div>

      <MessageBar :message="message.text" :type="message.type" />

      <template v-if="showCreateForm">
        <label>
          <span>考试日期</span>
          <input v-model="createForm.examDate" required type="date" />
        </label>
        <label>
          <span>批次时段</span>
          <select v-model="createForm.period">
            <option v-for="period in examBatches" :key="period">{{ period }}</option>
          </select>
        </label>
        <label>
          <span>批次容量</span>
          <input
            v-model.number="createForm.capacity"
            type="number"
            min="1"
            required
            placeholder="默认30人"
          />
        </label>
        <button class="primary-button" :disabled="saving" type="submit">
          <Plus :size="18" />
          <span>{{ saving ? '创建中' : '创建批次' }}</span>
        </button>
      </template>
    </form>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>批次列表</h3>
          <p>按日期和上午、下午批次统计报名和到场情况。</p>
        </div>
        <button class="icon-button" type="button" title="刷新" @click="loadBatches">
          <RefreshCcw :size="18" />
        </button>
      </div>

      <div class="summary-cards">
        <div class="summary-card">
          <div class="summary-icon">
            <CalendarDays :size="22" />
          </div>
          <div class="summary-content">
            <span class="summary-label">批次总数</span>
            <strong class="summary-value">{{ summary.totalBatches }}</strong>
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-icon capacity">
            <CalendarDays :size="22" />
          </div>
          <div class="summary-content">
            <span class="summary-label">总容量</span>
            <strong class="summary-value">{{ summary.totalCapacity }}</strong>
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-icon registered">
            <Users :size="22" />
          </div>
          <div class="summary-content">
            <span class="summary-label">报名人数</span>
            <strong class="summary-value">{{ summary.totalRegistered }}</strong>
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-icon attended">
            <CheckCircle2 :size="22" />
          </div>
          <div class="summary-content">
            <span class="summary-label">到场人数</span>
            <strong class="summary-value">{{ summary.totalAttended }}</strong>
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-icon rate">
            <TrendingUp :size="22" />
          </div>
          <div class="summary-content">
            <span class="summary-label">平均到场率</span>
            <strong class="summary-value">{{ summary.averageRate }}%</strong>
          </div>
        </div>
      </div>

      <form class="toolbar batch-toolbar" @submit.prevent="loadBatches">
        <label>
          <span>开始日期</span>
          <input v-model="filters.startDate" type="date" />
        </label>
        <label>
          <span>结束日期</span>
          <input v-model="filters.endDate" type="date" />
        </label>
        <button class="primary-button inline-button" type="submit">
          <Search :size="18" />
          <span>查询</span>
        </button>
      </form>

      <EmptyState
        v-if="!loading && batches.length === 0"
        title="暂无批次数据"
        description="请在左侧创建考试批次。"
      />

      <div v-else class="batch-list">
        <div v-for="batch in batches" :key="batch.id" class="batch-row">
          <div class="batch-header" @click="toggleExpand(batch)">
            <span class="expand-icon">
              <ChevronDown v-if="isExpanded(batch)" :size="18" />
              <ChevronRight v-else :size="18" />
            </span>
            <span class="batch-date">{{ batch.examDate }}</span>
            <span class="batch-badge" :class="getBatchBadgeClass(batch.period)">
              {{ batch.period }}
            </span>
            <span class="batch-status-badge" :class="batch.status === '开放' ? 'open' : 'closed'">
              {{ batch.status }}
            </span>
            <div class="batch-stats">
              <span class="stat-item">
                <span class="stat-label">报名</span>
                <span class="stat-value registered">{{ batch.registered }}</span>
              </span>
              <span class="stat-item">
                <span class="stat-label">到场</span>
                <span class="stat-value attended">{{ batch.attended }}</span>
              </span>
              <span class="stat-item">
                <span class="stat-label">到场率</span>
                <span class="stat-value rate">{{ batch.attendanceRate }}%</span>
              </span>
              <span class="stat-item">
                <span class="stat-label">剩余</span>
                <span class="stat-value remaining">{{ batch.remaining }}/{{ batch.capacity }}</span>
              </span>
            </div>
          </div>

          <div v-if="isExpanded(batch)" class="batch-detail">
            <div class="batch-actions">
              <div class="capacity-edit">
                <span class="capacity-label">容量：</span>
                <template v-if="editingCapacity === batch.id">
                  <input
                    v-model.number="editingValue"
                    type="number"
                    min="1"
                    class="capacity-input"
                    @keyup.enter="saveCapacity(batch)"
                    @keyup.escape="cancelEditCapacity"
                  />
                  <button class="small-button" type="button" @click="saveCapacity(batch)">保存</button>
                  <button class="small-button secondary" type="button" @click="cancelEditCapacity">取消</button>
                </template>
                <template v-else>
                  <span class="capacity-text">{{ batch.capacity }}人</span>
                  <button class="small-button" type="button" @click.stop="startEditCapacity(batch)">修改</button>
                </template>
              </div>
              <div class="action-buttons">
                <button
                  class="small-button"
                  :class="batch.status === '开放' ? 'secondary' : 'success'"
                  type="button"
                  @click.stop="toggleBatchStatus(batch)"
                >
                  {{ batch.status === '开放' ? '关闭批次' : '开放批次' }}
                </button>
                <button
                  class="small-button danger"
                  type="button"
                  @click.stop="deleteBatch(batch)"
                >
                  <Trash2 :size="14" />
                  删除
                </button>
              </div>
            </div>

            <EmptyState
              v-if="batch.appointments.length === 0"
              title="该批次暂无预约"
              description="暂无学员预约该批次。"
            />
            <DataTable v-else :columns="detailColumns" :rows="batch.appointments">
              <template #status="{ row }">
                <StatusBadge :status="row.status" />
              </template>
              <template #actions="{ row }">
                <button
                  v-if="row.status === '已预约'"
                  class="small-button success"
                  type="button"
                  @click.stop="markAttended(row)"
                >
                  签到
                </button>
              </template>
            </DataTable>
          </div>
        </div>
      </div>
    </section>
  </section>
</template>

<style scoped>
.summary-cards {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.summary-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border: 1px solid #dce3e8;
  border-radius: 8px;
  background: #fafbfc;
}

.summary-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: #e6f0f2;
  color: #1f7a8c;
}

.summary-icon.capacity {
  background: #f0e6f6;
  color: #7c3aed;
}

.summary-icon.registered {
  background: #eef2ff;
  color: #4f46e5;
}

.summary-icon.attended {
  background: #e4f6ec;
  color: #1e6b3f;
}

.summary-icon.rate {
  background: #fff4d9;
  color: #8a5a00;
}

.summary-content {
  display: grid;
  gap: 4px;
}

.summary-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 600;
}

.summary-value {
  font-size: 24px;
  font-weight: 800;
  color: #1f2937;
}

.batch-toolbar {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.batch-list {
  display: grid;
  gap: 10px;
}

.batch-row {
  border: 1px solid #dce3e8;
  border-radius: 8px;
  overflow: hidden;
}

.batch-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  background: #fafbfc;
  cursor: pointer;
  transition: background 0.15s ease;
}

.batch-header:hover {
  background: #f3f6f8;
}

.expand-icon {
  display: grid;
  place-items: center;
  color: #6b7280;
}

.batch-date {
  font-weight: 700;
  font-size: 15px;
  color: #1f2937;
  min-width: 110px;
}

.batch-badge {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.batch-badge.morning {
  background: #dbeafe;
  color: #1e40af;
}

.batch-badge.afternoon {
  background: #fed7aa;
  color: #9a3412;
}

.batch-status-badge {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.batch-status-badge.open {
  background: #e4f6ec;
  color: #1e6b3f;
}

.batch-status-badge.closed {
  background: #fde8e8;
  color: #a32929;
}

.batch-stats {
  display: flex;
  gap: 20px;
  margin-left: auto;
}

.stat-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 600;
}

.stat-value {
  font-size: 18px;
  font-weight: 800;
}

.stat-value.registered {
  color: #4f46e5;
}

.stat-value.attended {
  color: #1e6b3f;
}

.stat-value.rate {
  color: #8a5a00;
}

.stat-value.remaining {
  color: #7c3aed;
  font-size: 16px;
}

.batch-detail {
  padding: 16px 18px;
  border-top: 1px solid #e5ebef;
}

.batch-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e5ebef;
}

.capacity-edit {
  display: flex;
  align-items: center;
  gap: 8px;
}

.capacity-label {
  font-size: 13px;
  font-weight: 700;
  color: #374151;
}

.capacity-text {
  font-size: 14px;
  font-weight: 800;
  color: #1f2937;
}

.capacity-input {
  width: 80px;
  min-height: 32px;
  font-size: 14px;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.small-button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid #dce3e8;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.small-button:hover {
  background: #f3f6f8;
}

.small-button.success {
  background: #e4f6ec;
  color: #1e6b3f;
  border-color: #b6dcc8;
}

.small-button.success:hover {
  background: #d0ecd9;
}

.small-button.secondary {
  background: #eef2f7;
  color: #425466;
  border-color: #c8d1da;
}

.small-button.danger {
  background: #fde8e8;
  color: #a32929;
  border-color: #f0b8b8;
}

.small-button.danger:hover {
  background: #f8cece;
}

@media (max-width: 980px) {
  .summary-cards {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .batch-toolbar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .summary-cards {
    grid-template-columns: 1fr;
  }

  .batch-toolbar {
    grid-template-columns: 1fr;
  }

  .batch-header {
    flex-wrap: wrap;
    gap: 10px;
  }

  .batch-stats {
    margin-left: 0;
    width: 100%;
    justify-content: space-between;
  }

  .batch-actions {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }
}
</style>
