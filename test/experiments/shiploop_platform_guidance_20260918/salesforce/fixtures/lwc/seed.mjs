export function replaceRecordName(state, recordId, name) {
    const record = state.records.find((candidate) => candidate.id === recordId);
    record.name = name;
    return state;
}

export async function commitAndInvalidate({
    mutation,
    notifyRecordUpdateAvailable,
    recordIds
}) {
    mutation();
    notifyRecordUpdateAvailable(recordIds);
    return { submitted: true };
}
