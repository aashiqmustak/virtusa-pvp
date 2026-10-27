<script setup lang="ts">
import {computed} from 'vue'
import {inr} from '../stores/desk'
const props=defineProps<{monthly:Record<string,any>}>()
const rows=computed(()=>Object.entries(props.monthly||{}))
const max=computed(()=>Math.max(1,...rows.value.flatMap(([,r])=>[Number(r.operating_credits)||0,Number(r.operating_debits)||0])))
</script><template><div class="cash-chart"><p><span class="chart-key receipts"></span> Operating receipts <span class="chart-key expenses"></span> Operating expenses</p><div class="chart-columns" role="img" aria-label="Monthly operating receipts and expenses; exact figures in table below"><div v-for="([month,row]) in rows" class="chart-month"><div class="chart-bars"><div class="receipts" :style="{height:Math.max(0,Number(row.operating_credits))/max*100+'%'}" :title="inr(row.operating_credits)"></div><div class="expenses" :style="{height:Math.max(0,Number(row.operating_debits))/max*100+'%'}" :title="inr(row.operating_debits)"></div></div><small>{{month}}</small></div></div></div></template>