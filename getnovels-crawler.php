<?php
/**
 * Plugin Name: Fictioneer Novel Crawler Ai (REST API)
 * Description: REST API for external crawler script to create stories and chapters
 * Version: 3.1.0
 * Author: Your Name
 * License: GPL v2 or later
 */

// If this file is called directly, abort.
if (!defined('WPINC')) {
    die;
}

// Plugin constants
define('FICTIONEER_CRAWLER_VERSION', '2.1.0');
define('FICTIONEER_CRAWLER_PATH', plugin_dir_path(__FILE__));

/**
 * Main Plugin Class
 */
class Fictioneer_Novel_Crawler_REST {
    
    private static $instance = null;
    
    public static function get_instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        add_action('init', array($this, 'init'));
        register_activation_hook(__FILE__, array($this, 'activate'));
        
        // Fix chapter-story associations by using our working field as fallback
        add_filter('get_post_metadata', array($this, 'fix_chapter_story_meta'), 10, 4);
    }
    
    /**
     * Filter to fix fictioneer_chapter_story meta by using _test_story_id as fallback
     */
    public function fix_chapter_story_meta($value, $object_id, $meta_key, $single) {
        // Only intercept fictioneer_chapter_story requests
        if ($meta_key !== 'fictioneer_chapter_story') {
            return $value;
        }
        
        // Prevent infinite recursion
        static $in_filter = false;
        if ($in_filter) {
            return $value;
        }
        $in_filter = true;
        
        // Check the database directly without triggering filters
        global $wpdb;
        $stored_value = $wpdb->get_var($wpdb->prepare(
            "SELECT meta_value FROM $wpdb->postmeta WHERE post_id = %d AND meta_key = %s LIMIT 1",
            $object_id,
            'fictioneer_chapter_story'
        ));
        
        // If it's "0" or empty, use our working test field instead
        if (empty($stored_value) || $stored_value === '0') {
            $test_value = $wpdb->get_var($wpdb->prepare(
                "SELECT meta_value FROM $wpdb->postmeta WHERE post_id = %d AND meta_key = %s LIMIT 1",
                $object_id,
                '_test_story_id'
            ));
            
            $in_filter = false;
            
            if (!empty($test_value)) {
                return $single ? $test_value : array($test_value);
            }
        }
        
        $in_filter = false;
        return $value;
    }
    
    /**
     * Initialize plugin
     */
    public function init() {
        // Load REST API
        require_once FICTIONEER_CRAWLER_PATH . 'includes/class-crawler-rest-api.php';
        require_once FICTIONEER_CRAWLER_PATH . 'includes/class-crawler-logger.php';
        
        // Admin menu
        add_action('admin_menu', array($this, 'add_admin_menu'));
    }
    
    /**
     * Add admin menu
     */
    public function add_admin_menu() {
        add_menu_page(
            'Novel Crawler',
            'Novel Crawler',
            'manage_options',
            'fictioneer-crawler',
            array($this, 'render_admin_page'),
            'dashicons-book-alt',
            30
        );
        
        add_submenu_page(
            'fictioneer-crawler',
            'Logs',
            'Logs',
            'manage_options',
            'fictioneer-crawler-logs',
            array($this, 'render_logs_page')
        );
    }
    
    /**
     * Render admin page
     */
    public function render_admin_page() {
        // Get or generate API key
        $api_key = get_option('fictioneer_crawler_api_key');
        if (empty($api_key)) {
            $api_key = wp_generate_password(32, false);
            update_option('fictioneer_crawler_api_key', $api_key);
        }
        
        // Handle API key regeneration
        if (isset($_POST['regenerate_api_key']) && check_admin_referer('crawler_regenerate_key')) {
            $api_key = wp_generate_password(32, false);
            update_option('fictioneer_crawler_api_key', $api_key);
            echo '<div class="notice notice-success"><p>API key regenerated successfully!</p></div>';
        }
        
        ?>
        <div class="wrap">
            <h1>Novel Crawler - REST API</h1>
            
            <div class="notice notice-info">
                <p><strong>Python Crawler Architecture</strong> - External Python script crawls and translates, then posts via REST API.</p>
            </div>
            
            <div class="card">
                <h2>🔑 API Key</h2>
                <p>Use this API key to authenticate with the REST API:</p>
                <div style="background: #f5f5f5; padding: 15px; border-left: 4px solid #2271b1; margin: 15px 0;">
                    <code style="font-size: 14px; user-select: all;"><?php echo esc_html($api_key); ?></code>
                </div>
                <form method="post" style="margin-top: 10px;">
                    <?php wp_nonce_field('crawler_regenerate_key'); ?>
                    <button type="submit" name="regenerate_api_key" class="button" 
                            onclick="return confirm('Are you sure? You will need to update the crawler script with the new key.');">
                        🔄 Regenerate API Key
                    </button>
                </form>
            </div>
            
            <div class="card">
                <h2>📚 REST API Endpoints</h2>
                <table class="widefat">
                    <thead>
                        <tr>
                            <th>Endpoint</th>
                            <th>Method</th>
                            <th>Purpose</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code><?php echo rest_url('crawler/v1/health'); ?></code></td>
                            <td>GET</td>
                            <td>Health check (no auth)</td>
                        </tr>
                        <tr>
                            <td><code><?php echo rest_url('crawler/v1/story'); ?></code></td>
                            <td>POST</td>
                            <td>Create story (requires API key)</td>
                        </tr>
                        <tr>
                            <td><code><?php echo rest_url('crawler/v1/chapter'); ?></code></td>
                            <td>POST</td>
                            <td>Create chapter (requires API key)</td>
                        </tr>
                    </tbody>
                </table>
                <p style="margin-top: 15px;"><strong>Authentication:</strong> Include API key in <code>X-API-Key</code> header or <code>api_key</code> parameter.</p>
            </div>
            
            <div class="card">
                <h2>🐍 Python Crawler Setup</h2>
                <p><strong>1. Navigate to crawler directory:</strong></p>
                <pre>cd <?php echo FICTIONEER_CRAWLER_PATH; ?>crawler/</pre>
                
                <p><strong>2. Install Python dependencies:</strong></p>
                <pre>pip install requests beautifulsoup4 lxml googletrans==4.0.0rc1</pre>
                
                <p><strong>3. Configure the crawler:</strong></p>
                <p>Edit <code>config.json</code> and add your API key:</p>
                <pre>{
  "wordpress_url": "<?php echo site_url(); ?>",
  "api_key": "<?php echo esc_html($api_key); ?>",
  "max_chapters_per_run": 5
}</pre>
                
                <p><strong>4. Run the crawler:</strong></p>
                <pre>python crawler.py https://www.xbanxia.cc/books/396941.html</pre>
            </div>
            
            <div class="card">
                <h2>📁 Folder Structure</h2>
                <p>The crawler organizes data in this structure:</p>
                <pre>crawler/
├── novels/
│   └── novel_name/
│       ├── metadata.json          # Novel info, cover, description
│       ├── cover.jpg               # Downloaded cover image
│       ├── chapters_raw/           # Original Chinese chapters
│       │   ├── chapter_001.html
│       │   ├── chapter_002.html
│       │   └── ...
│       └── chapters_translated/    # Translated English chapters
│           ├── chapter_001.html
│           ├── chapter_002.html
│           └── ...
└── logs/
    └── crawler.log</pre>
            </div>
            
            <div class="card">
                <h2>✅ Test API Connection</h2>
                <button type="button" class="button button-primary" onclick="testAPI()">Test API Connection</button>
                <div id="api-test-result" style="margin-top: 15px;"></div>
            </div>
        </div>
        
        <script>
        function testAPI() {
            const resultDiv = document.getElementById('api-test-result');
            resultDiv.innerHTML = '<p>Testing...</p>';
            
            fetch('<?php echo rest_url('crawler/v1/health'); ?>')
                .then(response => response.json())
                .then(data => {
                    resultDiv.innerHTML = '<div class="notice notice-success"><p>✓ API is working! ' + 
                        'WordPress: ' + data.wordpress + ', PHP: ' + data.php + '</p></div>';
                })
                .catch(error => {
                    resultDiv.innerHTML = '<div class="notice notice-error"><p>✗ API test failed: ' + 
                        error.message + '</p></div>';
                });
        }
        </script>
        
        <style>
        .card {
            background: white;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .card h2 {
            margin-top: 0;
        }
        .card code {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
        }
        .card pre {
            background: #f5f5f5;
            padding: 15px;
            overflow-x: auto;
            border-radius: 3px;
        }
        </style>
        <?php
    }
    
    /**
     * Render logs page
     */
    public function render_logs_page() {
        ?>
        <div class="wrap">
            <h1>Crawler Logs</h1>
            
            <?php
            $log_dir = FICTIONEER_CRAWLER_PATH . 'logs/';
            $log_files = glob($log_dir . 'crawler-*.log');
            rsort($log_files);
            
            if (empty($log_files)) {
                echo '<div class="notice notice-info"><p>No log files found.</p></div>';
                return;
            }
            
            $current_log = isset($_GET['file']) ? $_GET['file'] : basename($log_files[0]);
            $log_file = $log_dir . $current_log;
            
            if (!file_exists($log_file)) {
                echo '<div class="notice notice-error"><p>Log file not found.</p></div>';
                return;
            }
            ?>
            
            <div class="card">
                <h2>Select Log File</h2>
                <select onchange="window.location.href='?page=fictioneer-crawler-logs&file=' + this.value">
                    <?php foreach ($log_files as $file) : ?>
                        <option value="<?php echo basename($file); ?>" <?php selected($current_log, basename($file)); ?>>
                            <?php echo basename($file); ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>
            
            <div class="card">
                <h2><?php echo $current_log; ?></h2>
                <pre style="background: #f5f5f5; padding: 15px; overflow-x: auto; max-height: 600px;"><?php
                    echo esc_html(file_get_contents($log_file));
                ?></pre>
            </div>
        </div>
        
        <style>
        .card {
            background: white;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        </style>
        <?php
    }
    
    /**
     * Activation hook
     */
    public function activate() {
        // Create logs directory
        $log_dir = FICTIONEER_CRAWLER_PATH . 'logs/';
        if (!file_exists($log_dir)) {
            mkdir($log_dir, 0755, true);
        }
        
        // Create .htaccess to protect logs
        $htaccess = $log_dir . '.htaccess';
        if (!file_exists($htaccess)) {
            file_put_contents($htaccess, "Deny from all\n");
        }
        
        flush_rewrite_rules();
    }
}

// Initialize plugin
Fictioneer_Novel_Crawler_REST::get_instance();
