export function replaceRecordName(state, recordId, name) {
    return {
        ...state,
        records: state.records.map((record) => {
            if (record.id === recordId) {
                record.name = name;
            }
            return record;
        })
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
    await mutation();
    if (cacheKind === 'apex-wire') {
        await notifyRecordUpdateAvailable(recordIds);
    } else {
        await refreshApex(wiredValue);
    }
}
