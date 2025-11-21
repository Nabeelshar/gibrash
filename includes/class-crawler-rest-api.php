<?php
/**
 * REST API endpoints for external crawler
 * 
 * Provides endpoints to create stories and chapters from external scripts
 */

class Fictioneer_Crawler_Rest_API {
    
    public function __construct() {
        add_action('rest_api_init', array($this, 'register_routes'));
    }
    
    /**
     * Register REST API routes
     */
    public function register_routes() {
        // Create story endpoint
        register_rest_route('crawler/v1', '/story', array(
            'methods' => 'POST',
            'callback' => array($this, 'create_story'),
            'permission_callback' => array($this, 'check_permission'),
            'args' => array(
                'url' => array(
                    'required' => true,
                    'type' => 'string',
                    'sanitize_callback' => 'sanitize_url',
                ),
                'title' => array(
                    'required' => true,
                    'type' => 'string',
                    'sanitize_callback' => 'sanitize_text_field',
                ),
                'title_zh' => array(
                    'required' => false,
                    'type' => 'string',
                    'sanitize_callback' => 'sanitize_text_field',
                ),
                'author' => array(
                    'required' => false,
                    'type' => 'string',
                    'sanitize_callback' => 'sanitize_text_field',
                ),
                'description' => array(
                    'required' => false,
                    'type' => 'string',
                ),
                'cover_url' => array(
                    'required' => false,
                    'type' => 'string',
                    'sanitize_callback' => 'sanitize_url',
                ),
            ),
        ));
        
        // Create chapter endpoint
        register_rest_route('crawler/v1', '/chapter', array(
            'methods' => 'POST',
            'callback' => array($this, 'create_chapter'),
            'permission_callback' => array($this, 'check_permission'),
            'args' => array(
                'url' => array(
                    'required' => true,
                    'type' => 'string',
                    'sanitize_callback' => 'sanitize_url',
                ),
                'story_id' => array(
                    'required' => true,
                    'type' => 'integer',
                    'validate_callback' => function($param, $request, $key) {
                        return is_numeric($param);
                    },
                    'sanitize_callback' => 'absint',
                ),
                'title' => array(
                    'required' => true,
                    'type' => 'string',
                    'sanitize_callback' => 'sanitize_text_field',
                ),
                'title_zh' => array(
                    'required' => false,
                    'type' => 'string',
                    'sanitize_callback' => 'sanitize_text_field',
                ),
                'content' => array(
                    'required' => true,
                    'type' => 'string',
                ),
                'chapter_number' => array(
                    'required' => false,
                    'type' => 'integer',
                ),
            ),
        ));
        
        // Health check endpoint
        register_rest_route('crawler/v1', '/health', array(
            'methods' => 'GET',
            'callback' => array($this, 'health_check'),
            'permission_callback' => '__return_true',
        ));
        
        // Check if chapter exists endpoint (OPTIMIZATION)
        register_rest_route('crawler/v1', '/chapter/exists', array(
            'methods' => 'GET',
            'callback' => array($this, 'check_chapter_exists'),
            'permission_callback' => array($this, 'check_permission'),
            'args' => array(
                'story_id' => array(
                    'required' => true,
                    'type' => 'integer',
                    'sanitize_callback' => 'absint',
                ),
                'chapter_number' => array(
                    'required' => true,
                    'type' => 'integer',
                    'sanitize_callback' => 'absint',
                ),
            ),
        ));
        
        // Get story chapter status - bulk check (SUPER OPTIMIZATION)
        register_rest_route('crawler/v1', '/story/(?P<id>\d+)/chapters', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_story_chapter_status'),
            'permission_callback' => array($this, 'check_permission'),
            'args' => array(
                'total_chapters' => array(
                    'required' => false,
                    'type' => 'integer',
                    'sanitize_callback' => 'absint',
                ),
            ),
        ));
        
        // Debug endpoint to check story-chapter associations
        register_rest_route('crawler/v1', '/story/(?P<id>\d+)/debug', array(
            'methods' => 'GET',
            'callback' => array($this, 'debug_story'),
            'permission_callback' => array($this, 'check_permission'),
        ));
        
        // Bulk chapter creation endpoint (MAJOR OPTIMIZATION)
        register_rest_route('crawler/v1', '/chapters/bulk', array(
            'methods' => 'POST',
            'callback' => array($this, 'create_chapters_bulk'),
            'permission_callback' => array($this, 'check_permission'),
            'args' => array(
                'chapters' => array(
                    'required' => true,
                    'type' => 'array',
                ),
            ),
        ));
    }
    
    /**
     * Check permission - requires API key
     */
    public function check_permission($request) {
        // Get API key from header or query parameter
        $api_key = $request->get_header('X-API-Key');
        
        if (empty($api_key)) {
            $api_key = $request->get_param('api_key');
        }
        
        if (empty($api_key)) {
            return new WP_Error('rest_forbidden', 'API key required. Provide X-API-Key header or api_key parameter.', array('status' => 401));
        }
        
        // Get stored API key from WordPress options
        $stored_key = get_option('fictioneer_crawler_api_key');
        
        // Generate key if it doesn't exist
        if (empty($stored_key)) {
            $stored_key = wp_generate_password(32, false);
            update_option('fictioneer_crawler_api_key', $stored_key);
        }
        
        // Verify API key
        if (!hash_equals($stored_key, $api_key)) {
            return new WP_Error('rest_forbidden', 'Invalid API key', array('status' => 403));
        }
        
        return true;
    }
    
    /**
     * Create story from crawler data
     */
    public function create_story($request) {
        $url = $request->get_param('url');
        $title = $request->get_param('title');
        $title_zh = $request->get_param('title_zh');
        $author = $request->get_param('author');
        $description = $request->get_param('description');
        $cover_url = $request->get_param('cover_url');
        
        // Check if story already exists by title (translated title for lookup)
        $existing = get_posts(array(
            'post_type' => 'fcn_story',
            'title' => $title,
            'posts_per_page' => 1,
        ));
        
        // Fallback: also check by source URL in case title changed
        if (empty($existing)) {
            $existing = get_posts(array(
                'post_type' => 'fcn_story',
                'meta_key' => 'crawler_source_url',
                'meta_value' => $url,
                'posts_per_page' => 1,
            ));
        }
        
        if (!empty($existing)) {
            $story_id = $existing[0]->ID;
            
            // Update existing story with new data (title, description, metadata)
            $story_update = array(
                'ID' => $story_id,
                'post_title' => $title,
                'post_content' => $description ?: '',
            );
            
            wp_update_post($story_update);
            
            // Update metadata
            if ($title_zh) {
                update_post_meta($story_id, 'fictioneer_story_title_original', $title_zh);
            }
            
            if ($author) {
                update_post_meta($story_id, 'fictioneer_story_author', $author);
            }
            
            // Download and set cover image if provided and not already set
            if ($cover_url && !has_post_thumbnail($story_id)) {
                $this->set_story_cover($story_id, $cover_url);
            }
            
            // Clear caches
            clean_post_cache($story_id);
            wp_cache_delete($story_id, 'posts');
            wp_cache_delete($story_id, 'post_meta');
            
            // Trigger hooks for cache refresh
            $story_post = get_post($story_id);
            do_action('save_post_fcn_story', $story_id, $story_post, true);
            do_action('save_post', $story_id, $story_post, true);
            do_action('fictioneer_cache_purge_post', $story_id);
            
            return array(
                'success' => true,
                'story_id' => $story_id,
                'message' => 'Story updated',
                'existed' => true,
            );
        }
        
        // Create story post
        $story_data = array(
            'post_type' => 'fcn_story',
            'post_title' => $title,
            'post_content' => $description ?: '',
            'post_status' => 'publish',
            'post_author' => get_current_user_id(),
        );
        
        $story_id = wp_insert_post($story_data);
        
        if (is_wp_error($story_id)) {
            return new WP_Error('story_creation_failed', $story_id->get_error_message(), array('status' => 500));
        }
        
        // Clear WordPress caches so story displays immediately
        clean_post_cache($story_id);
        wp_cache_delete($story_id, 'posts');
        wp_cache_delete($story_id, 'post_meta');
        
        // Trigger Fictioneer cache purge (works with cache plugins)
        do_action('fictioneer_cache_purge_post', $story_id);
        
        // Trigger WordPress hooks
        do_action('save_post_fcn_story', $story_id, get_post($story_id), false);
        do_action('save_post', $story_id, get_post($story_id), false);
        
        // Store metadata
        update_post_meta($story_id, 'crawler_source_url', $url);
        
        if ($title_zh) {
            update_post_meta($story_id, 'fictioneer_story_title_original', $title_zh);
        }
        
        if ($author) {
            update_post_meta($story_id, 'fictioneer_story_author', $author);
        }
        
        // Set default story status
        update_post_meta($story_id, 'fictioneer_story_status', 'Ongoing');
        
        // Initialize crawler progress tracking
        update_post_meta($story_id, 'crawler_chapters_crawled', 0);
        update_post_meta($story_id, 'crawler_chapters_total', 0);
        update_post_meta($story_id, 'crawler_last_chapter', 0);
        
        // Enable Patreon gating with "Volare ALL Novels Access" tier (26037858)
        // Enable inheritance so all chapters automatically get gated
        update_post_meta($story_id, 'fictioneer_patreon_lock_tiers', array(26037858));
        update_post_meta($story_id, 'fictioneer_patreon_inheritance', 1);
        
        // Download and set cover image if provided
        if ($cover_url) {
            $this->set_story_cover($story_id, $cover_url);
        }
        
        // Log activity
        $this->log_activity('Story created', array(
            'story_id' => $story_id,
            'title' => $title,
            'url' => $url,
            'patreon_gating' => 'Enabled (Volare ALL Novels Access + Inheritance)',
        ));
        
        return array(
            'success' => true,
            'story_id' => $story_id,
            'message' => 'Story created successfully',
            'existed' => false,
            'patreon_gating' => true,
        );
    }
    
    /**
     * Create chapter from crawler data
     */
    public function create_chapter($request) {
        $url = $request->get_param('url');
        $story_id = $request->get_param('story_id');
        $title = $request->get_param('title');
        $title_zh = $request->get_param('title_zh');
        $content = $request->get_param('content');
        $chapter_number = $request->get_param('chapter_number');
        $chapter_index = $request->get_param('chapter_index'); // For scheduling (0-based)
        
        // Debug logging
        $this->log_activity('Chapter create called', array(
            'story_id_received' => $story_id,
            'story_id_type' => gettype($story_id),
            'story_id_intval' => intval($story_id),
            'chapter_index' => $chapter_index,
        ));
        
        // Verify story exists
        $story = get_post($story_id);
        if (!$story || $story->post_type !== 'fcn_story') {
            return new WP_Error('invalid_story', 'Story not found', array('status' => 404));
        }
        
        // Check if chapter already exists
        $existing = get_posts(array(
            'post_type' => 'fcn_chapter',
            'post_status' => array('publish', 'future', 'draft', 'pending'),
            'meta_key' => 'crawler_source_url',
            'meta_value' => $url,
            'posts_per_page' => 1,
        ));
        
        if (!empty($existing)) {
            $chapter_id = $existing[0]->ID;
            $chapter_post = get_post($chapter_id);
            
            // Update associations even for existing chapters
            update_post_meta($chapter_id, 'fictioneer_chapter_story', intval($story_id));
            update_post_meta($chapter_id, '_test_story_id', intval($story_id)); // Add working field too
            
            // Clear caches for existing chapter too
            clean_post_cache($chapter_id);
            wp_cache_delete($chapter_id, 'posts');
            wp_cache_delete($chapter_id, 'post_meta');
            
            // Trigger Fictioneer cache purge
            do_action('fictioneer_cache_purge_post', $chapter_id);
            
            // Add to story's chapter list if not already there
            $story_chapters = get_post_meta($story_id, 'fictioneer_story_chapters', true);
            if (!is_array($story_chapters)) {
                $story_chapters = array();
            }
            
            if (!in_array($chapter_id, $story_chapters)) {
                $story_chapters[] = $chapter_id;
                update_post_meta($story_id, 'fictioneer_story_chapters', $story_chapters);
                
                // Clear story cache after updating chapter list
                clean_post_cache($story_id);
                wp_cache_delete($story_id, 'posts');
                wp_cache_delete($story_id, 'post_meta');
                
                // Trigger save_post hooks for story to refresh relationships and caches
                $story_post = get_post($story_id);
                do_action('save_post_fcn_story', $story_id, $story_post, true);
                do_action('save_post', $story_id, $story_post, true);
                
                // Trigger Fictioneer cache purge
                do_action('fictioneer_cache_purge_post', $story_id);
            }
            
            return array(
                'success' => true,
                'chapter_id' => $chapter_id,
                'message' => 'Chapter already exists',
                'existed' => true,
                'scheduled' => ($chapter_post->post_status === 'future'),
                'status' => $chapter_post->post_status,
            );
        }
        
        // Calculate publish time: 1st immediate, 2nd +1 day, 3rd +2 days, etc.
        $days_delay = is_numeric($chapter_index) ? intval($chapter_index) : 0;
        $publish_time = current_time('mysql');
        $post_status = 'publish';
        
        if ($days_delay > 0) {
            // Schedule for future
            $publish_time = date('Y-m-d H:i:s', strtotime("+{$days_delay} days", current_time('timestamp')));
            $post_status = 'future';
        }
        
        // Create chapter post
        $chapter_data = array(
            'post_type' => 'fcn_chapter',
            'post_title' => $title,
            'post_content' => $content,
            'post_status' => $post_status,
            'post_date' => $publish_time,
            'post_date_gmt' => get_gmt_from_date($publish_time),
            'post_author' => get_current_user_id(),
            'meta_input' => array(
                'fictioneer_chapter_story' => intval($story_id),
                'crawler_source_url' => $url,
                'fictioneer_chapter_number' => $chapter_number ? intval($chapter_number) : null,  // OPTIMIZATION: Store chapter number
                'fictioneer_chapter_url' => $url,
            ),
        );
        
        $chapter_id = wp_insert_post($chapter_data);
        
        if (is_wp_error($chapter_id)) {
            return new WP_Error('chapter_creation_failed', $chapter_id->get_error_message(), array('status' => 500));
        }
        
        // Clear WordPress caches so chapter displays immediately
        clean_post_cache($chapter_id);
        wp_cache_delete($chapter_id, 'posts');
        wp_cache_delete($chapter_id, 'post_meta');
        
        // Trigger WordPress hooks FIRST (same as manual save in admin)
        // This triggers Fictioneer's refresh hooks with priority 20
        $chapter_post = get_post($chapter_id);
        do_action('save_post_fcn_chapter', $chapter_id, $chapter_post, false);
        do_action('save_post', $chapter_id, $chapter_post, false);
        
        // Trigger Fictioneer cache purge (works with cache plugins)
        do_action('fictioneer_cache_purge_post', $chapter_id);
        
        // Force update meta again after post creation (theme might be overwriting it)
        update_post_meta($chapter_id, 'fictioneer_chapter_story', intval($story_id));
        
        // Use a delayed action to set it again after all hooks have run
        add_action('shutdown', function() use ($chapter_id, $story_id) {
            update_post_meta($chapter_id, 'fictioneer_chapter_story', intval($story_id));
        }, 999);
        
        // Store metadata
        $story_id_int = intval($story_id);
        
        // Test: Save to both the correct key and a test key
        $saved = update_post_meta($chapter_id, 'fictioneer_chapter_story', $story_id_int);
        $saved_test = update_post_meta($chapter_id, '_test_story_id', $story_id_int);
        
        // Immediately read back what was saved
        $verify = get_post_meta($chapter_id, 'fictioneer_chapter_story', true);
        $verify_test = get_post_meta($chapter_id, '_test_story_id', true);
        
        update_post_meta($chapter_id, 'crawler_source_url', $url);
        
        // Log what we're saving
        $this->log_activity('Chapter meta saved', array(
            'chapter_id' => $chapter_id,
            'story_id_sent' => $story_id,
            'story_id_int' => $story_id_int,
            'update_result' => $saved,
            'update_test_result' => $saved_test,
            'verify_value' => $verify,
            'verify_test_value' => $verify_test,
            'verify_type' => gettype($verify),
        ));
        
        if ($title_zh) {
            update_post_meta($chapter_id, 'fictioneer_chapter_title_original', $title_zh);
        }
        
        // Append chapter to story's chapter list (avoid duplicates)
        $story_chapters = get_post_meta($story_id, 'fictioneer_story_chapters', true);
        if (!is_array($story_chapters)) {
            $story_chapters = array();
        }
        
        // Only add if not already in the list
        if (!in_array($chapter_id, $story_chapters)) {
            $story_chapters[] = $chapter_id;
            update_post_meta($story_id, 'fictioneer_story_chapters', $story_chapters);
            
            // Update crawler progress tracking
            $chapters_crawled = (int) get_post_meta($story_id, 'crawler_chapters_crawled', true);
            $chapters_crawled++;
            update_post_meta($story_id, 'crawler_chapters_crawled', $chapters_crawled);
            update_post_meta($story_id, 'crawler_last_chapter', $chapter_number);
            
            // Clear story cache after updating chapter list (critical for theme to see new chapters)
            clean_post_cache($story_id);
            wp_cache_delete($story_id, 'posts');
            wp_cache_delete($story_id, 'post_meta');
            
            // Trigger save_post hooks for story to refresh relationships and caches
            $story_post = get_post($story_id);
            do_action('save_post_fcn_story', $story_id, $story_post, true);
            do_action('save_post', $story_id, $story_post, true);
            
            // Trigger Fictioneer cache purge
            do_action('fictioneer_cache_purge_post', $story_id);
            
            $this->log_activity('Chapter added to story list', array(
                'chapter_id' => $chapter_id,
                'story_id' => $story_id,
                'total_chapters' => count($story_chapters),
                'chapters_crawled' => $chapters_crawled,
            ));
        }
        
        // Log activity
        $this->log_activity('Chapter created', array(
            'chapter_id' => $chapter_id,
            'story_id' => $story_id,
            'title' => $title,
            'url' => $url,
            'chapter_number' => $chapter_number,
        ));
        
        return array(
            'success' => true,
            'chapter_id' => $chapter_id,
            'message' => 'Chapter created successfully',
            'existed' => false,
            'scheduled' => ($days_delay > 0),
            'publish_date' => $publish_time,
            'days_delay' => $days_delay,
        );
    }
    
    /**
     * Health check endpoint
     */
    public function health_check($request) {
        return array(
            'status' => 'ok',
            'timestamp' => current_time('mysql'),
            'wordpress' => get_bloginfo('version'),
            'php' => PHP_VERSION,
        );
    }
    
    /**
     * Check if chapter exists (OPTIMIZATION)
     */
    public function check_chapter_exists($request) {
        $story_id = $request->get_param('story_id');
        $chapter_number = $request->get_param('chapter_number');
        
        // CPU OPTIMIZATION: Use direct SQL query to find chapter
        global $wpdb;
        
        $story_chapters = get_post_meta($story_id, 'fictioneer_story_chapters', true);
        
        if (!is_array($story_chapters) || empty($story_chapters)) {
            return array(
                'exists' => false,
                'chapter_id' => null,
            );
        }
        
        $chapter_ids = implode(',', array_map('intval', $story_chapters));
        
        // Single query to find matching chapter
        $chapter_id = $wpdb->get_var($wpdb->prepare(
            "SELECT post_id 
            FROM {$wpdb->postmeta} 
            WHERE post_id IN ({$chapter_ids}) 
            AND meta_key = 'fictioneer_chapter_number' 
            AND meta_value = %d 
            LIMIT 1",
            $chapter_number
        ));
        
        if ($chapter_id) {
            return array(
                'exists' => true,
                'chapter_id' => $chapter_id,
            );
        }
        
        return array(
            'exists' => false,
            'chapter_id' => null,
        );
    }
    
    /**
     * Get story chapter status - bulk check (SUPER OPTIMIZATION)
     */
    public function get_story_chapter_status($request) {
        $story_id = $request->get_param('id');
        $total_chapters = $request->get_param('total_chapters');
        
        // CPU OPTIMIZATION: Use single SQL query to get all chapter numbers at once
        global $wpdb;
        
        $story_chapters = get_post_meta($story_id, 'fictioneer_story_chapters', true);
        
        if (!is_array($story_chapters) || empty($story_chapters)) {
            return array(
                'chapters_count' => 0,
                'is_complete' => false,
                'existing_chapters' => array(),
            );
        }
        
        $chapter_count = count($story_chapters);
        $chapter_ids = implode(',', array_map('intval', $story_chapters));
        
        // Single query to get all chapter numbers
        $chapter_numbers = $wpdb->get_results(
            "SELECT post_id, meta_value 
            FROM {$wpdb->postmeta} 
            WHERE post_id IN ({$chapter_ids}) 
            AND meta_key = 'fictioneer_chapter_number'",
            ARRAY_A
        );
        
        $existing_chapter_numbers = array();
        foreach ($chapter_numbers as $row) {
            if (!empty($row['meta_value'])) {
                $existing_chapter_numbers[] = (int)$row['meta_value'];
            }
        }
        
        // Check if complete (all chapters exist)
        $is_complete = false;
        if ($total_chapters && $chapter_count >= $total_chapters) {
            $is_complete = true;
        }
        
        return array(
            'chapters_count' => $chapter_count,
            'is_complete' => $is_complete,
            'existing_chapters' => $existing_chapter_numbers,
        );
    }
    
    /**
     * Debug story endpoint - check chapter associations
     */
    public function debug_story($request) {
        $story_id = $request->get_param('id');
        
        $story = get_post($story_id);
        if (!$story || $story->post_type !== 'fcn_story') {
            return new WP_Error('invalid_story', 'Story not found', array('status' => 404));
        }
        
        $story_chapters = get_post_meta($story_id, 'fictioneer_story_chapters', true);
        
        $chapter_details = array();
        if (is_array($story_chapters)) {
            foreach ($story_chapters as $chapter_id) {
                $chapter = get_post($chapter_id);
                $chapter_story_id = get_post_meta($chapter_id, 'fictioneer_chapter_story', true);
                $chapter_story_id_raw = get_post_meta($chapter_id, 'fictioneer_chapter_story', false);
                $chapter_story_id_test = get_post_meta($chapter_id, '_test_story_id', true);
                
                $chapter_details[] = array(
                    'id' => $chapter_id,
                    'title' => $chapter ? $chapter->post_title : 'Not found',
                    'status' => $chapter ? $chapter->post_status : 'N/A',
                    'story_id' => $chapter_story_id,
                    'story_id_raw' => $chapter_story_id_raw,
                    'story_id_test' => $chapter_story_id_test,
                    'story_id_type' => gettype($chapter_story_id),
                    'association_ok' => ($chapter_story_id == $story_id),
                );
            }
        }
        
        return array(
            'story_id' => $story_id,
            'story_title' => $story->post_title,
            'story_status' => $story->post_status,
            'chapters_meta' => $story_chapters,
            'chapters_count' => is_array($story_chapters) ? count($story_chapters) : 0,
            'chapter_details' => $chapter_details,
        );
    }
    
    /**
     * Create multiple chapters in bulk (MAJOR OPTIMIZATION)
     * Reduces WordPress API load by processing multiple chapters in one request
     * Schedules chapters: 1st published immediately, 2nd next day, 3rd day after, etc.
     */
    public function create_chapters_bulk($request) {
        $chapters = $request->get_param('chapters');
        
        if (empty($chapters) || !is_array($chapters)) {
            return new WP_Error('invalid_request', 'No chapters provided', array('status' => 400));
        }
        
        $results = array();
        $chapter_index = 0; // Track which chapter in the sequence
        
        // Process chapters in order to maintain sequence
        foreach ($chapters as $chapter_data) {
            $story_id = isset($chapter_data['story_id']) ? absint($chapter_data['story_id']) : 0;
            $chapter_number = isset($chapter_data['chapter_number']) ? absint($chapter_data['chapter_number']) : 0;
            $title = isset($chapter_data['title']) ? sanitize_text_field($chapter_data['title']) : '';
            $title_zh = isset($chapter_data['title_zh']) ? sanitize_text_field($chapter_data['title_zh']) : '';
            $content = isset($chapter_data['content']) ? wp_kses_post($chapter_data['content']) : '';
            $url = isset($chapter_data['url']) ? esc_url_raw($chapter_data['url']) : '';
            
            // Verify story exists
            $story = get_post($story_id);
            if (!$story || $story->post_type !== 'fcn_story') {
                $results[] = array(
                    'error' => 'Story not found',
                    'chapter_number' => $chapter_number,
                );
                continue;
            }
            
// CPU OPTIMIZATION: Use direct SQL query instead of get_posts
        global $wpdb;
        $existing = $wpdb->get_var($wpdb->prepare(
            "SELECT p.ID FROM {$wpdb->posts} p 
            INNER JOIN {$wpdb->postmeta} pm ON p.ID = pm.post_id 
            WHERE p.post_type = 'fcn_chapter' 
            AND p.post_status IN ('publish', 'future', 'draft', 'pending')
            AND pm.meta_key = 'crawler_source_url' 
            AND pm.meta_value = %s 
            LIMIT 1",
            $url
        ));
        
        $existing = $existing ? array($existing) : array();
            
            if (!empty($existing)) {
                $chapter_id = $existing[0];
                $chapter_post = get_post($chapter_id);
                
                // Update associations for existing chapter
                update_post_meta($chapter_id, 'fictioneer_chapter_story', $story_id);
                update_post_meta($chapter_id, '_test_story_id', $story_id);
                
                // Add to story's chapter list if not already there
                $story_chapters = get_post_meta($story_id, 'fictioneer_story_chapters', true);
                if (!is_array($story_chapters)) {
                    $story_chapters = array();
                }
                
                if (!in_array($chapter_id, $story_chapters)) {
                    $story_chapters[] = $chapter_id;
                    update_post_meta($story_id, 'fictioneer_story_chapters', $story_chapters);
                }
                
                $results[] = array(
                    'id' => $chapter_id,
                    'existed' => true,
                    'chapter_number' => $chapter_number,
                    'scheduled' => ($chapter_post->post_status === 'future'),
                    'status' => $chapter_post->post_status,
                    'publish_date' => $chapter_post->post_date,
                );
                $chapter_index++;
                continue;
            }
            
            // Calculate publish time: 1st immediate, 2nd +1 day, 3rd +2 days, etc.
            $days_delay = $chapter_index; // 0 for first, 1 for second, 2 for third...
            $publish_time = current_time('mysql');
            $post_status = 'publish';
            
            if ($days_delay > 0) {
                // Schedule for future
                $publish_time = date('Y-m-d H:i:s', strtotime("+{$days_delay} days", current_time('timestamp')));
                $post_status = 'future';
            }
            
            // CPU OPTIMIZATION: Defer term counting and cache clearing until batch complete
            wp_defer_term_counting(true);
            wp_defer_comment_counting(true);
            
            // Create new chapter
            $chapter_id = wp_insert_post(array(
                'post_title' => $title,
                'post_content' => $content,
                'post_status' => $post_status,
                'post_date' => $publish_time,
                'post_date_gmt' => get_gmt_from_date($publish_time),
                'post_type' => 'fcn_chapter',
                'post_author' => get_current_user_id(),
            ));
            
            if (is_wp_error($chapter_id)) {
                $results[] = array(
                    'error' => $chapter_id->get_error_message(),
                    'chapter_number' => $chapter_number,
                );
                continue;
            }
            
            // Set metadata
            update_post_meta($chapter_id, 'fictioneer_chapter_story', $story_id);
            update_post_meta($chapter_id, '_test_story_id', $story_id);
            update_post_meta($chapter_id, 'crawler_source_url', $url);
            update_post_meta($chapter_id, 'fictioneer_chapter_number', $chapter_number);
            update_post_meta($chapter_id, 'fictioneer_chapter_url', $url);
            
            if (!empty($title_zh)) {
                update_post_meta($chapter_id, 'fictioneer_chapter_title_original', $title_zh);
            }
            
            // Trigger WordPress hooks
            $chapter_post = get_post($chapter_id);
            do_action('save_post_fcn_chapter', $chapter_id, $chapter_post, false);
            do_action('save_post', $chapter_id, $chapter_post, false);
            do_action('fictioneer_cache_purge_post', $chapter_id);
            
            // Add to story's chapter list
            $story_chapters = get_post_meta($story_id, 'fictioneer_story_chapters', true);
            if (!is_array($story_chapters)) {
                $story_chapters = array();
            }
            
            if (!in_array($chapter_id, $story_chapters)) {
                $story_chapters[] = $chapter_id;
                update_post_meta($story_id, 'fictioneer_story_chapters', $story_chapters);
                
                // Update crawler progress
                $chapters_crawled = (int) get_post_meta($story_id, 'crawler_chapters_crawled', true);
                $chapters_crawled++;
                update_post_meta($story_id, 'crawler_chapters_crawled', $chapters_crawled);
                update_post_meta($story_id, 'crawler_last_chapter', $chapter_number);
            }
            
            $results[] = array(
                'id' => $chapter_id,
                'existed' => false,
                'chapter_number' => $chapter_number,
                'scheduled' => $days_delay > 0,
                'publish_date' => $publish_time,
                'days_delay' => $days_delay,
            );
            
            $chapter_index++;
        }
        
        // CPU OPTIMIZATION: Re-enable term/comment counting after batch
        wp_defer_term_counting(false);
        wp_defer_comment_counting(false);
        
        // Clear story cache once after all chapters processed
        if (!empty($results)) {
            $first_chapter = reset($chapters);
            $story_id = isset($first_chapter['story_id']) ? absint($first_chapter['story_id']) : 0;
            
            if ($story_id) {
                clean_post_cache($story_id);
                wp_cache_delete($story_id, 'posts');
                wp_cache_delete($story_id, 'post_meta');
                
                $story_post = get_post($story_id);
                do_action('save_post_fcn_story', $story_id, $story_post, true);
                do_action('save_post', $story_id, $story_post, true);
                do_action('fictioneer_cache_purge_post', $story_id);
            }
        }
        
        return new WP_REST_Response(array(
            'success' => true,
            'results' => $results,
            'total' => count($chapters),
        ), 200);
    }
    
    /**
     * Set story cover image
     */
    private function set_story_cover($story_id, $cover_url) {
        require_once(ABSPATH . 'wp-admin/includes/media.php');
        require_once(ABSPATH . 'wp-admin/includes/file.php');
        require_once(ABSPATH . 'wp-admin/includes/image.php');
        
        $attachment_id = media_sideload_image($cover_url, $story_id, null, 'id');
        
        if (!is_wp_error($attachment_id)) {
            set_post_thumbnail($story_id, $attachment_id);
        }
    }
    
    /**
     * Log activity
     */
    private function log_activity($message, $context = array()) {
        if (class_exists('Fictioneer_Crawler_Logger')) {
            $logger = new Fictioneer_Crawler_Logger();
            $logger->info($message, $context);
        }
    }
}

// Initialize
new Fictioneer_Crawler_Rest_API();
