import {test,expect} from 'vitest'
import {inr,label} from './desk'
test('missing money remains unknown while zero remains zero',()=>{expect(inr(null)).toBe('Insufficient evidence');expect(inr(0)).toContain('0');expect(inr(100000)).toContain('1,00,000')})
test('status is readable',()=>expect(label('needs_evidence')).toBe('Action needed'))
