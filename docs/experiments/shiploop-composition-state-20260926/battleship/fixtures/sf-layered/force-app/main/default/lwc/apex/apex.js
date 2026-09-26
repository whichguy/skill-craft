// Call Apex through this module: it unwraps ServiceResult, shows a toast on failure and returns data.
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
export async function callApex(host, method, params) {
    const result = await method(params);
    if (!result.ok) { host.dispatchEvent(new ShowToastEvent({ title: 'Error', message: result.message, variant: 'error' })); throw new Error(result.errorCode); }
    return result.data;
}
