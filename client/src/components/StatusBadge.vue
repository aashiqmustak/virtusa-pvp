<script setup lang="ts">
import {displayText,displayJson,initials} from "../stores/presentation"
import {label} from '../stores/desk'
defineProps<{value:string}>()
</script>
<template><span class="badge" :class="value">{{displayText(label(value))}}</span></template>
