-- Sample Slack user data for testing MCP server integration
-- Connect to insight_mesh database
\c insight_mesh;

-- Insert sample Slack user data for t@example.com
INSERT INTO slack_users (
    id, 
    name, 
    real_name, 
    display_name, 
    email, 
    is_admin, 
    is_owner, 
    is_bot, 
    deleted, 
    team_id, 
    data,
    created_at,
    updated_at
) VALUES (
    'U12345TRAVIS',  -- Sample Slack user ID
    'travis.frisinger',
    'Travis Frisinger',
    'Travis Frisinger',
    't@example.com',
    true,  -- is_admin
    true,  -- is_owner
    false, -- is_bot
    false, -- deleted
    'T12345TEAM',  -- team_id
    '{"profile": {"title": "Founder", "phone": "", "skype": "", "real_name": "Travis Frisinger", "real_name_normalized": "Travis Frisinger", "display_name": "Travis Frisinger", "display_name_normalized": "Travis Frisinger", "fields": null, "status_text": "", "status_emoji": "", "status_expiration": 0, "avatar_hash": "abc123", "email": "t@example.com", "first_name": "Travis", "last_name": "Frisinger", "image_24": "https://example.com/avatar_24.jpg", "image_32": "https://example.com/avatar_32.jpg", "image_48": "https://example.com/avatar_48.jpg", "image_72": "https://example.com/avatar_72.jpg", "image_192": "https://example.com/avatar_192.jpg", "image_512": "https://example.com/avatar_512.jpg"}}',
    NOW(),
    NOW()
) ON CONFLICT (email) DO UPDATE SET
    name = EXCLUDED.name,
    real_name = EXCLUDED.real_name,
    display_name = EXCLUDED.display_name,
    is_admin = EXCLUDED.is_admin,
    is_owner = EXCLUDED.is_owner,
    data = EXCLUDED.data,
    updated_at = NOW();

-- Insert a sample channel
INSERT INTO slack_channels (
    id,
    name,
    is_private,
    is_archived,
    created,
    creator,
    num_members,
    purpose,
    topic,
    data,
    created_at,
    updated_at
) VALUES (
    'C12345GENERAL',
    'general',
    false,
    false,
    NOW(),
    'U12345TRAVIS',
    1,
    'General discussion',
    'Welcome to the team!',
    '{"is_channel": true, "is_group": false, "is_im": false, "is_mpim": false, "is_private": false, "created": 1234567890, "is_archived": false, "is_general": true, "unlinked": 0, "name_normalized": "general", "is_shared": false, "is_org_shared": false}',
    NOW(),
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    purpose = EXCLUDED.purpose,
    topic = EXCLUDED.topic,
    updated_at = NOW();

SELECT 'Sample Slack data inserted successfully!' as result; 