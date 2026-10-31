@IsTest
private class SLGymOracleTest {
    private static final String ACCESS_PERMISSION_SET = 'SLGym_Access';

    @IsTest
    static void selfMembershipBindsToCallingUser() {
        User member = makeUser(false);

        System.runAs(member) {
            System.assertEquals('null', SLGymController.getMyMembership());
            Map<String, Object> saved = asMap(
                SLGymController.saveMyMembership('Self Bound', 'self@example.invalid', 'Strength', 'Coached')
            );
            System.assertEquals(String.valueOf(member.Id), (String)saved.get('loginUserId'));
        }

        SLGymMember__c stored = membershipForUser(member.Id);
        System.assertEquals(String.valueOf(member.Id), stored.LoginUserId__c);
        System.assertEquals('Self Bound', stored.FullName__c);
        System.assertEquals('self@example.invalid', stored.Email__c);
        System.assertEquals('Strength', stored.Goal__c);
        System.assertEquals('Coached', stored.Plan__c);
        System.assertEquals('Active', stored.Status__c);
    }

    @IsTest
    static void savePreservesFrozenStatus() {
        User member = makeUser(false);
        User admin = makeUser(true);
        Id memberId = seedSelf(member, 'Frozen Member', 'frozen@example.invalid', 'Strength', 'Basic');
        setStatusAsAdmin(admin, memberId, 'Frozen');

        System.runAs(member) {
            SLGymController.saveMyMembership('Frozen Member Edited', 'frozen-edited@example.invalid', 'Mobility', 'Coached');
        }

        SLGymMember__c stored = membershipForUser(member.Id);
        System.assertEquals(memberId, stored.Id);
        System.assertEquals(String.valueOf(member.Id), stored.LoginUserId__c);
        System.assertEquals('Frozen Member Edited', stored.FullName__c);
        System.assertEquals('frozen-edited@example.invalid', stored.Email__c);
        System.assertEquals('Mobility', stored.Goal__c);
        System.assertEquals('Coached', stored.Plan__c);
        System.assertEquals('Frozen', stored.Status__c);
    }

    @IsTest
    static void savePreservesCancelledStatus() {
        User member = makeUser(false);
        User admin = makeUser(true);
        Id memberId = seedSelf(member, 'Cancelled Member', 'cancelled@example.invalid', 'Strength', 'Basic');
        setStatusAsAdmin(admin, memberId, 'Cancelled');

        System.runAs(member) {
            SLGymController.saveMyMembership('Cancelled Member Edited', 'cancelled-edited@example.invalid', 'Mobility', 'Coached');
        }

        SLGymMember__c stored = membershipForUser(member.Id);
        System.assertEquals(memberId, stored.Id);
        System.assertEquals(String.valueOf(member.Id), stored.LoginUserId__c);
        System.assertEquals('Cancelled Member Edited', stored.FullName__c);
        System.assertEquals('cancelled-edited@example.invalid', stored.Email__c);
        System.assertEquals('Mobility', stored.Goal__c);
        System.assertEquals('Coached', stored.Plan__c);
        System.assertEquals('Cancelled', stored.Status__c);
    }

    @IsTest
    static void selfCanFreezeAndResumeAnActiveMembership() {
        User member = makeUser(false);
        Id memberId = seedSelf(member, 'Status Member', 'status@example.invalid', 'Strength', 'Basic');

        System.runAs(member) {
            Map<String, Object> frozen = asMap(SLGymController.setMyStatus('Frozen'));
            System.assertEquals('Frozen', (String)frozen.get('status'));
            Map<String, Object> resumed = asMap(SLGymController.setMyStatus('Active'));
            System.assertEquals('Active', (String)resumed.get('status'));
        }

        SLGymMember__c stored = membershipForUser(member.Id);
        System.assertEquals(memberId, stored.Id);
        System.assertEquals('Active', stored.Status__c);
        System.assertEquals(0, visitCount(memberId));
    }

    @IsTest
    static void cancelledSelfCannotResumeEvenForAdmin() {
        User adminMember = makeUser(true);
        Id memberId = seedSelf(adminMember, 'Admin Member', 'admin-member@example.invalid', 'Strength', 'Basic');
        setStatusAsAdmin(adminMember, memberId, 'Cancelled');
        SLGymMember__c beforeCall = memberById(memberId);

        System.runAs(adminMember) {
            expectStatusRefused('Active');
            expectStatusRefused('Frozen');
        }

        SLGymMember__c stored = membershipForUser(adminMember.Id);
        assertSameMember(beforeCall, stored);
        System.assertEquals(0, visitCount(memberId));
    }

    @IsTest
    static void foreignMemberAccessIsRefusedWithoutAVisit() {
        User owner = makeUser(false);
        User outsider = makeUser(false);
        Id memberId = seedSelf(owner, 'Private Member', 'private@example.invalid', 'Strength', 'Basic');
        SLGymMember__c beforeCall = memberById(memberId);

        System.runAs(outsider) {
            expectMember360Refused(String.valueOf(memberId));
            expectCheckInRefused(String.valueOf(memberId));
        }

        SLGymMember__c afterCall = memberById(memberId);
        assertSameMember(beforeCall, afterCall);
        System.assertEquals(0, visitCount(memberId));
    }

    @IsTest
    static void ordinaryUsersCannotListOrSaveAdmins() {
        User ordinary = makeUser(false);
        String marker = uniqueName('Must Not Persist');

        System.runAs(ordinary) {
            expectListRefused();
            expectAdminSaveRefused(null, marker, 'ordinary-admin@example.invalid', 'Strength', 'Basic', 'Active');
        }

        System.assertEquals(0, [SELECT count() FROM SLGymMember__c WHERE FullName__c = :marker]);
    }

    @IsTest
    static void adminCanCreateUpdateListAndInspect360() {
        User admin = makeUser(true);
        Id linkedMemberId = seedSelf(admin, 'Admin Self', 'admin-self@example.invalid', 'Strength', 'Coached');
        DateTime sameTime = System.now().addDays(-2);
        insert new List<SLGymVisit__c>{
            new SLGymVisit__c(Member__c = linkedMemberId, CheckedInAt__c = sameTime, Coaching__c = 'Older same-time coaching'),
            new SLGymVisit__c(Member__c = linkedMemberId, CheckedInAt__c = sameTime, Coaching__c = 'Latest same-time coaching')
        };
        SLGymVisit__c expectedLatest = [
            SELECT Id, Coaching__c
            FROM SLGymVisit__c
            WHERE Member__c = :linkedMemberId
            ORDER BY CheckedInAt__c DESC, Id DESC
            LIMIT 1
        ];

        String unlinkedName = uniqueName('Admin Created');
        String unlinkedId;
        System.runAs(admin) {
            Map<String, Object> updated = asMap(SLGymController.adminSave(
                String.valueOf(linkedMemberId), 'Admin Self Edited', 'admin-self-edited@example.invalid',
                'Mobility', 'Basic', 'Frozen'
            ));
            System.assertEquals(String.valueOf(linkedMemberId), (String)updated.get('id'));

            Map<String, Object> created = asMap(SLGymController.adminSave(
                null, unlinkedName, 'unlinked@example.invalid', 'Strength', 'Coached', 'Active'
            ));
            unlinkedId = (String)created.get('id');

            List<Object> listed = asList(SLGymController.listMembers());
            System.assert(containsMember(listed, String.valueOf(linkedMemberId)));
            System.assert(containsMember(listed, unlinkedId));

            Map<String, Object> view = asMap(SLGymController.member360(String.valueOf(linkedMemberId)));
            System.assertEquals(2, (Integer)view.get('visitCount'));
            System.assertEquals(expectedLatest.Coaching__c, (String)view.get('coaching'));
        }

        SLGymMember__c linked = memberById(linkedMemberId);
        System.assertEquals(String.valueOf(admin.Id), linked.LoginUserId__c);
        System.assertEquals('Admin Self Edited', linked.FullName__c);
        System.assertEquals('admin-self-edited@example.invalid', linked.Email__c);
        System.assertEquals('Mobility', linked.Goal__c);
        System.assertEquals('Basic', linked.Plan__c);
        System.assertEquals('Frozen', linked.Status__c);

        SLGymMember__c unlinked = memberById((Id)unlinkedId);
        System.assertEquals(null, unlinked.LoginUserId__c);
        System.assertEquals(unlinkedName, unlinked.FullName__c);
        System.assertEquals('Active', unlinked.Status__c);
    }

    @IsTest
    static void sequentialCheckInsDeduplicateAndYesterdayAllowsNewVisit() {
        User member = makeUser(false);
        Id memberId = seedSelf(member, 'Dedup Member', 'dedup@example.invalid', 'Strength', 'Basic');
        String firstVisitId;
        String secondVisitId;

        System.runAs(member) {
            DateTime yesterdayAtNoon = DateTime.newInstance(Date.today().addDays(-1), Time.newInstance(12, 0, 0, 0));
            insert new SLGymVisit__c(
                Member__c = memberId,
                CheckedInAt__c = yesterdayAtNoon,
                Coaching__c = 'Yesterday stored coaching'
            );

            Map<String, Object> first = asMap(SLGymController.checkIn(String.valueOf(memberId)));
            Map<String, Object> second = asMap(SLGymController.checkIn(String.valueOf(memberId)));
            firstVisitId = (String)first.get('visitId');
            secondVisitId = (String)second.get('visitId');
            System.assertEquals(firstVisitId, secondVisitId);
            System.assertEquals(2, (Integer)first.get('visitCount'));
            System.assertEquals(2, (Integer)second.get('visitCount'));
        }

        List<SLGymVisit__c> visits = visitHistory(memberId);
        System.assertEquals(2, visits.size());
        System.assertNotEquals(String.valueOf(visits[0].Id), firstVisitId);
        System.assertEquals(firstVisitId, secondVisitId);
        System.assertEquals('Yesterday stored coaching', visits[0].Coaching__c);
        System.assertNotEquals(visits[0].CheckedInAt__c, visits[1].CheckedInAt__c);
        System.assertEquals('Basic', memberById(memberId).Plan__c);
    }

    @IsTest
    static void statusIsCheckedBeforeSameDayDeduplication() {
        User member = makeUser(false);
        User admin = makeUser(true);
        Id memberId = seedSelf(member, 'Blocked Check In', 'blocked@example.invalid', 'Strength', 'Basic');
        String firstVisitId;

        System.runAs(member) {
            firstVisitId = (String)asMap(SLGymController.checkIn(String.valueOf(memberId))).get('visitId');
        }

        setStatusAsAdmin(admin, memberId, 'Frozen');
        SLGymMember__c frozen = memberById(memberId);
        System.runAs(member) {
            expectCheckInRefused(String.valueOf(memberId));
        }
        System.assertEquals(1, visitCount(memberId));
        System.assertEquals(firstVisitId, String.valueOf(visitHistory(memberId)[0].Id));
        assertSameMember(frozen, memberById(memberId));

        setStatusAsAdmin(admin, memberId, 'Cancelled');
        SLGymMember__c cancelled = memberById(memberId);
        System.runAs(member) {
            expectCheckInRefused(String.valueOf(memberId));
        }
        System.assertEquals(1, visitCount(memberId));
        assertSameMember(cancelled, memberById(memberId));
    }

    @IsTest
    static void coachingIsStoredPerPlanAndSurvivesProfileEdits() {
        User coached = makeUser(false);
        User basic = makeUser(false);
        Id coachedId = seedSelf(coached, 'Coached Member', 'coached@example.invalid', 'Strength', 'Coached');
        Id basicId = seedSelf(basic, 'Basic Member', 'basic@example.invalid', 'Cardio', 'Basic');
        String coachedText;
        String basicText;

        System.runAs(coached) {
            coachedText = (String)asMap(SLGymController.checkIn(String.valueOf(coachedId))).get('coaching');
            SLGymController.saveMyMembership('Coached Member Edited', 'coached-edited@example.invalid', 'Mobility', 'Coached');
            Map<String, Object> view = asMap(SLGymController.member360(String.valueOf(coachedId)));
            System.assertEquals(coachedText, (String)view.get('coaching'));
        }
        System.runAs(basic) {
            basicText = (String)asMap(SLGymController.checkIn(String.valueOf(basicId))).get('coaching');
        }

        SLGymVisit__c coachedVisit = visitHistory(coachedId)[0];
        SLGymVisit__c basicVisit = visitHistory(basicId)[0];
        System.assert(coachedText.toLowerCase().contains('strength'), coachedText);
        System.assertEquals(coachedText, coachedVisit.Coaching__c);
        System.assert(coachedVisit.Coaching__c.toLowerCase().contains('strength'), coachedVisit.Coaching__c);
        System.assert(basicText.toLowerCase().contains('independent training'), basicText);
        System.assertEquals(basicText, basicVisit.Coaching__c);
        System.assert(basicVisit.Coaching__c.toLowerCase().contains('independent training'), basicVisit.Coaching__c);
        System.assertEquals('Mobility', membershipForUser(coached.Id).Goal__c);
        System.assertEquals('Coached', membershipForUser(coached.Id).Plan__c);
    }

    @IsTest
    static void invalidInputsRefuseAndLeaveStateUnchanged() {
        User admin = makeUser(true);
        Id memberId = seedSelf(admin, 'Valid Member', 'valid@example.invalid', 'Strength', 'Basic');
        String badAdminName = uniqueName('Invalid Id Must Not Persist');

        System.runAs(admin) {
            expectSaveRefused('Changed Name', 'changed@example.invalid', 'Strength', 'Premium');
            expectSaveRefused('', 'changed@example.invalid', 'Strength', 'Basic');
            expectSaveRefused('Changed Name', 'not-an-email', 'Strength', 'Basic');
            expectSaveRefused('Changed Name', 'changed@example.invalid', '', 'Basic');
            expectStatusRefused('Archived');
            expectMember360Refused('not-an-id');
            expectAdminSaveRefused('not-an-id', badAdminName, 'invalid-id@example.invalid', 'Strength', 'Basic', 'Active');
        }

        SLGymMember__c stored = membershipForUser(admin.Id);
        System.assertEquals(memberId, stored.Id);
        System.assertEquals('Valid Member', stored.FullName__c);
        System.assertEquals('valid@example.invalid', stored.Email__c);
        System.assertEquals('Strength', stored.Goal__c);
        System.assertEquals('Basic', stored.Plan__c);
        System.assertEquals('Active', stored.Status__c);
        System.assertEquals(0, visitCount(memberId));
        System.assertEquals(0, [SELECT count() FROM SLGymMember__c WHERE FullName__c = :badAdminName]);
    }

    private static User makeUser(Boolean admin) {
        List<Profile> profiles = [
            SELECT Id, PermissionsModifyAllData
            FROM Profile
            WHERE UserType = 'Standard' AND PermissionsModifyAllData = :admin AND UserLicense.Name IN ('Salesforce', 'Salesforce Platform')
            ORDER BY Id
            LIMIT 1
        ];
        System.assertEquals(1, profiles.size(), 'An appropriate role profile must exist');
        System.assertEquals(admin, profiles[0].PermissionsModifyAllData);

        String token = EncodingUtil.convertToHex(Crypto.generateAesKey(128)).toLowerCase();
        String email = 'gym-' + token + '@example.invalid';
        User created = new User(
            Alias = 'gymtest',
            Email = email,
            EmailEncodingKey = 'UTF-8',
            FirstName = 'Gym',
            LastName = 'Oracle',
            LanguageLocaleKey = 'en_US',
            LocaleSidKey = 'en_US',
            ProfileId = profiles[0].Id,
            TimeZoneSidKey = 'America/Los_Angeles',
            Username = email
        );

        User current = [SELECT Id FROM User WHERE Id = :UserInfo.getUserId()];
        System.runAs(current) {
            insert created;
        }

        PermissionSet accessSet = [
            SELECT Id
            FROM PermissionSet
            WHERE Name = :ACCESS_PERMISSION_SET
            LIMIT 1
        ];
        System.runAs(created) {
            insert new PermissionSetAssignment(PermissionSetId = accessSet.Id, AssigneeId = UserInfo.getUserId());
        }
        return created;
    }

    private static Id seedSelf(User user, String fullName, String email, String goal, String plan) {
        System.runAs(user) {
            SLGymController.saveMyMembership(fullName, email, goal, plan);
        }
        return membershipForUser(user.Id).Id;
    }

    private static void setStatusAsAdmin(User admin, Id memberId, String status) {
        SLGymMember__c current = memberById(memberId);
        System.runAs(admin) {
            SLGymController.adminSave(
                String.valueOf(memberId), current.FullName__c, current.Email__c,
                current.Goal__c, current.Plan__c, status
            );
        }
    }

    private static String uniqueName(String prefix) {
        return prefix + ' ' + EncodingUtil.convertToHex(Crypto.generateAesKey(128)).toLowerCase();
    }

    private static Map<String, Object> asMap(String value) {
        return (Map<String, Object>)JSON.deserializeUntyped(value);
    }

    private static List<Object> asList(String value) {
        return (List<Object>)JSON.deserializeUntyped(value);
    }

    private static Boolean containsMember(List<Object> rows, String memberId) {
        for (Object row : rows) {
            Map<String, Object> member = (Map<String, Object>)row;
            if ((String)member.get('id') == memberId) return true;
        }
        return false;
    }

    private static SLGymMember__c membershipForUser(Id userId) {
        String loginUserId = String.valueOf(userId);
        List<SLGymMember__c> rows = [
            SELECT Id, LoginUserId__c, FullName__c, Email__c, Goal__c, Plan__c, Status__c
            FROM SLGymMember__c
            WHERE LoginUserId__c = :loginUserId
            LIMIT 1
        ];
        System.assertEquals(1, rows.size(), 'Expected exactly one persisted self membership');
        return rows[0];
    }

    private static SLGymMember__c memberById(Id memberId) {
        return [
            SELECT Id, LoginUserId__c, FullName__c, Email__c, Goal__c, Plan__c, Status__c
            FROM SLGymMember__c
            WHERE Id = :memberId
            LIMIT 1
        ];
    }

    private static void assertSameMember(SLGymMember__c expected, SLGymMember__c actual) {
        System.assertEquals(expected.Id, actual.Id);
        System.assertEquals(expected.LoginUserId__c, actual.LoginUserId__c);
        System.assertEquals(expected.FullName__c, actual.FullName__c);
        System.assertEquals(expected.Email__c, actual.Email__c);
        System.assertEquals(expected.Goal__c, actual.Goal__c);
        System.assertEquals(expected.Plan__c, actual.Plan__c);
        System.assertEquals(expected.Status__c, actual.Status__c);
    }

    private static List<SLGymVisit__c> visitHistory(Id memberId) {
        return [
            SELECT Id, Member__c, CheckedInAt__c, Coaching__c
            FROM SLGymVisit__c
            WHERE Member__c = :memberId
            ORDER BY CheckedInAt__c ASC, Id ASC
        ];
    }

    private static Integer visitCount(Id memberId) {
        return [SELECT count() FROM SLGymVisit__c WHERE Member__c = :memberId];
    }

    private static void expectStatusRefused(String status) {
        Boolean refused = false;
        try {
            SLGymController.setMyStatus(status);
        } catch (AuraHandledException expected) {
            refused = true;
        }
        System.assert(refused, 'setMyStatus must refuse ' + status + ' with AuraHandledException');
    }

    private static void expectSaveRefused(String fullName, String email, String goal, String plan) {
        Boolean refused = false;
        try {
            SLGymController.saveMyMembership(fullName, email, goal, plan);
        } catch (AuraHandledException expected) {
            refused = true;
        }
        System.assert(refused, 'saveMyMembership must refuse invalid input with AuraHandledException');
    }

    private static void expectAdminSaveRefused(String memberId, String fullName, String email, String goal, String plan, String status) {
        Boolean refused = false;
        try {
            SLGymController.adminSave(memberId, fullName, email, goal, plan, status);
        } catch (AuraHandledException expected) {
            refused = true;
        }
        System.assert(refused, 'adminSave must refuse with AuraHandledException');
    }

    private static void expectListRefused() {
        Boolean refused = false;
        try {
            SLGymController.listMembers();
        } catch (AuraHandledException expected) {
            refused = true;
        }
        System.assert(refused, 'listMembers must refuse for an ordinary user with AuraHandledException');
    }

    private static void expectMember360Refused(String memberId) {
        Boolean refused = false;
        try {
            SLGymController.member360(memberId);
        } catch (AuraHandledException expected) {
            refused = true;
        }
        System.assert(refused, 'member360 must refuse invalid or foreign access with AuraHandledException');
    }

    private static void expectCheckInRefused(String memberId) {
        Boolean refused = false;
        try {
            SLGymController.checkIn(memberId);
        } catch (AuraHandledException expected) {
            refused = true;
        }
        System.assert(refused, 'checkIn must refuse invalid or foreign access with AuraHandledException');
    }
}
