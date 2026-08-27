Gave the identity provider demo its groups as exported content, filed under `/groups`, and stopped creating one in code.

The demo showed content-backed users and no groups at all, so the group half of the content layer had nothing on screen. A group created by the setup handler *and* present in the content payload is created twice on a fresh site, which is the shape the export round trip makes easy to reach; the payload is the single source now, and `group_container_id` tells the site where those groups live. @ericof
