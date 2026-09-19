export function replaceRecordName(state, recordId, name) {
    return {
        ...state,
        records: state.records.map((record) =>
            record.id === recordId ? { ...record, name } : record
        )
    };
}

export async function commitAndInvalidate({
    cacheKind,
    mutation,
    notifyRecordUpdateAvailable,
    recordIds,
    refreshApex,
    wiredValue
}) {
    const result = await mutation();
    if (cacheKind === 'apex-wire') {
        await refreshApex(wiredValue);
    } else if (cacheKind === 'lds-record') {
        await notifyRecordUpdateAvailable(recordIds.map((recordId) => ({ recordId })));
    } else {
        throw new Error(`Unsupported cache kind: ${cacheKind}`);
    }
    return result;
}
