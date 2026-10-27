<script setup lang="ts">
import {displayText,displayJson,initials} from "../stores/presentation"
import {reactive} from 'vue'
import {api} from '../api'
import {desk} from '../stores/desk'
const emit=defineEmits(['created'])
const form=reactive({applicant:'',business:'',purpose:'',requested_amount:1000000,tenure_months:36,synthetic:true})
async function submit(){desk.busy=true;desk.error='';try{const c=await api('/applications',form);emit('created',c.id)}catch(e){desk.error=(e as Error).message}finally{desk.busy=false}}
</script>
<template><div class="page-heading"><div><div class="eyebrow">INTAKE / NEW APPLICATION</div><h1>Start with the business.</h1><p>Capture the application details and gather the supporting records.</p></div></div><form class="panel intake" @submit.prevent="submit"><h2>Applicant details</h2><div class="form-grid"><label>Applicant name<input v-model="form.applicant" required minlength="2" maxlength="120" placeholder="Full name as shown on identity records"></label><label>Business name<input v-model="form.business" required minlength="2" maxlength="120" placeholder="Registered business name"></label><label>Requested amount · INR<input type="number" v-model.number="form.requested_amount" required min="1" max="100000000"></label><label>Tenure · months<input type="number" v-model.number="form.tenure_months" required min="1" max="120"></label></div><label>Purpose of loan<textarea v-model="form.purpose" required minlength="3" maxlength="500" placeholder="Describe the proposed use of funds"></textarea></label><div class="notice">Every application is assessed against the current credit policy and reviewed by an authorized decision-maker.</div><button class="primary" :disabled="desk.busy">Create application →</button></form></template>
