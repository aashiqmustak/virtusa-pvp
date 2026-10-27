<script setup lang="ts">
import {computed} from 'vue'
import {displayText} from '../stores/presentation'
const props=defineProps<{value:any}>()
const rows=computed(()=>{const out:{label:string,value:string}[]=[];function walk(v:any,path:string){if(v===null||v===undefined)return;if(typeof v==='object'){Object.entries(v).forEach(([k,x])=>{if(!['synthetic','mock_only','simulation','model_mode'].includes(k))walk(x,path?path+' · '+k:k)})}else out.push({label:displayText(path.replace(/_/g,' ')),value:typeof v==='boolean'?(v?'Yes':'No'):displayText(v)})}walk(props.value,'Detail');return out})
</script><template><dl class="record-summary"><div v-for="(row,i) in rows" :key="i"><dt>{{row.label}}</dt><dd>{{row.value}}</dd></div><p v-if="!rows.length">No details recorded yet.</p></dl></template>