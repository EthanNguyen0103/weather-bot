#!/usr/bin/env python3
"""
LeetCode Random Challenge, Idea (Approach), and Answer (C++ Solution Code) helper for MS Teams Bot.
Supports:
  - !leetcode / !leetcode random [easy|medium|hard]
  - !leetcode ideal / !leetcode idea / !leetcode hint
  - !leetcode answer / !leetcode ans / !leetcode solution
  - !leetcode random ideal / !leetcode random answer / !leetcode full
"""

import html
import json
import random
import re
import urllib.parse
import urllib.request
from pathlib import Path

SEEN_LEETCODE_FILE = Path(__file__).parent / ".seen_leetcode.txt"
LAST_LEETCODE_FILE = Path(__file__).parent / ".last_leetcode_problem.json"

# Curated bank of classic LeetCode Interview Problems with Vietnamese + English Idea & optimal C++ Answer
CURATED_PROBLEMS = [
    {
        "id": "1",
        "title": "Two Sum",
        "difficulty": "Easy",
        "topics": "Array, Hash Table",
        "url": "https://leetcode.com/problems/two-sum/",
        "description": (
            "Given an array of integers nums and an integer target, return indices of the two numbers "
            "such that they add up to target. You may assume that each input would have exactly one solution."
        ),
        "example": "Input: nums = [2,7,11,15], target = 9  =>  Output: [0,1] (Because nums[0] + nums[1] == 9)",
        "idea": (
            "• Dùng Hash Map (unordered_map<int, int>) lưu giá trị đã duyệt qua dưới dạng {num: index}.\n"
            "• Với mỗi phần tử nums[i], kiểm tra xem phần bù (target - nums[i]) đã có trong Hash Map chưa.\n"
            "• Nếu có thì trả về {seen[target - nums[i]], i} ngay lập tức trong 1 vòng lặp duy nhất.\n"
            "• Độ phức tạp: Time O(n) | Space O(n)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    vector<int> twoSum(vector<int>& nums, int target) {\n"
            "        unordered_map<int, int> seen;\n"
            "        for (int i = 0; i < (int)nums.size(); ++i) {\n"
            "            int diff = target - nums[i];\n"
            "            if (seen.count(diff)) return {seen[diff], i};\n"
            "            seen[nums[i]] = i;\n"
            "        }\n"
            "        return {};\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "3",
        "title": "Longest Substring Without Repeating Characters",
        "difficulty": "Medium",
        "topics": "Hash Table, String, Sliding Window",
        "url": "https://leetcode.com/problems/longest-substring-without-repeating-characters/",
        "description": (
            "Given a string s, find the length of the longest substring without duplicate characters."
        ),
        "example": 'Input: s = "abcabcbb"  =>  Output: 3 (The answer is "abc", with the length of 3)',
        "idea": (
            "• Dùng kỹ thuật Cửa sổ trượt (Sliding Window) với 2 con trỏ left và right.\n"
            "• Dùng mảng đánh dấu vị trí xuất hiện gần nhất của từng ký tự ASCII: vector<int> last_idx(128, -1).\n"
            "• Khi gặp ký tự s[right] đã nằm trong cửa sổ hiện tại (last_idx[c] >= left), dịch left nhảy tới last_idx[c] + 1.\n"
            "• Cập nhật độ dài lớn nhất max_len = max(max_len, right - left + 1).\n"
            "• Độ phức tạp: Time O(n) | Space O(1)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    int lengthOfLongestSubstring(string s) {\n"
            "        vector<int> last_idx(128, -1);\n"
            "        int left = 0, max_len = 0;\n"
            "        for (int right = 0; right < (int)s.size(); ++right) {\n"
            "            unsigned char c = s[right];\n"
            "            if (last_idx[c] >= left) left = last_idx[c] + 1;\n"
            "            last_idx[c] = right;\n"
            "            max_len = max(max_len, right - left + 1);\n"
            "        }\n"
            "        return max_len;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "11",
        "title": "Container With Most Water",
        "difficulty": "Medium",
        "topics": "Array, Two Pointers, Greedy",
        "url": "https://leetcode.com/problems/container-with-most-water/",
        "description": (
            "You are given an integer array height of length n. Find two lines that together with the x-axis "
            "form a container, such that the container contains the most water."
        ),
        "example": "Input: height = [1,8,6,2,5,4,8,3,7]  =>  Output: 49",
        "idea": (
            "• Đặt 2 con trỏ ở 2 đầu mảng: l = 0, r = height.size() - 1.\n"
            "• Diện tích hiện tại: min(height[l], height[r]) * (r - l).\n"
            "• Tham lam (Greedy): luôn dịch chuyển con trỏ có chiều cao thấp hơn vào trong vì giữ lại cột thấp không thể tạo diện tích lớn hơn khi chiều rộng giảm.\n"
            "• Độ phức tạp: Time O(n) | Space O(1)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    int maxArea(vector<int>& height) {\n"
            "        int l = 0, r = (int)height.size() - 1, best = 0;\n"
            "        while (l < r) {\n"
            "            best = max(best, min(height[l], height[r]) * (r - l));\n"
            "            if (height[l] < height[r]) ++l;\n"
            "            else --r;\n"
            "        }\n"
            "        return best;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "15",
        "title": "3Sum",
        "difficulty": "Medium",
        "topics": "Array, Two Pointers, Sorting",
        "url": "https://leetcode.com/problems/3sum/",
        "description": (
            "Given an integer array nums, return all the triplets [nums[i], nums[j], nums[k]] such that "
            "i != j, i != k, and j != k, and nums[i] + nums[j] + nums[k] == 0. Solution set must not contain duplicate triplets."
        ),
        "example": "Input: nums = [-1,0,1,2,-1,-4]  =>  Output: [[-1,-1,2],[-1,0,1]]",
        "idea": (
            "• Sắp xếp mảng tăng dần: sort(nums.begin(), nums.end()).\n"
            "• Duyệt i từ 0..n-3 (bỏ qua nếu nums[i] trùng với nums[i-1]).\n"
            "• Dùng 2 con trỏ l = i + 1 và r = n - 1 để tìm cặp có tổng bằng -nums[i], đồng thời bỏ qua các phần tử trùng lặp.\n"
            "• Độ phức tạp: Time O(n^2) | Space O(1) (không tính output)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    vector<vector<int>> threeSum(vector<int>& nums) {\n"
            "        sort(nums.begin(), nums.end());\n"
            "        vector<vector<int>> res;\n"
            "        int n = nums.size();\n"
            "        for (int i = 0; i < n - 2 && nums[i] <= 0; ++i) {\n"
            "            if (i > 0 && nums[i] == nums[i - 1]) continue;\n"
            "            int l = i + 1, r = n - 1;\n"
            "            while (l < r) {\n"
            "                int s = nums[i] + nums[l] + nums[r];\n"
            "                if (s < 0) ++l;\n"
            "                else if (s > 0) --r;\n"
            "                else {\n"
            "                    res.push_back({nums[i], nums[l++], nums[r--]});\n"
            "                    while (l < r && nums[l] == nums[l - 1]) ++l;\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "        return res;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "20",
        "title": "Valid Parentheses",
        "difficulty": "Easy",
        "topics": "String, Stack",
        "url": "https://leetcode.com/problems/valid-parentheses/",
        "description": (
            "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', "
            "determine if the input string is valid (open brackets closed by same type in correct order)."
        ),
        "example": 'Input: s = "()[]{}"  =>  Output: true',
        "idea": (
            "• Sử dụng cấu trúc Ngăn xếp (stack<char>).\n"
            "• Khi gặp dấu ngoặc mở '(', '[', '{' thì đẩy dấu ngoặc đóng tương ứng ')', ']', '}' vào stack.\n"
            "• Khi gặp dấu ngoặc đóng, kiểm tra đỉnh stack có khớp không; nếu stack rỗng hoặc lệch cặp thì trả về false.\n"
            "• Cuối cùng trả về st.empty().\n"
            "• Độ phức tạp: Time O(n) | Space O(n)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    bool isValid(string s) {\n"
            "        stack<char> st;\n"
            "        for (char c : s) {\n"
            "            if (c == '(') st.push(')');\n"
            "            else if (c == '[') st.push(']');\n"
            "            else if (c == '{') st.push('}');\n"
            "            else {\n"
            "                if (st.empty() || st.top() != c) return false;\n"
            "                st.pop();\n"
            "            }\n"
            "        }\n"
            "        return st.empty();\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "42",
        "title": "Trapping Rain Water",
        "difficulty": "Hard",
        "topics": "Array, Two Pointers, Dynamic Programming, Monotonic Stack",
        "url": "https://leetcode.com/problems/trapping-rain-water/",
        "description": (
            "Given n non-negative integers representing an elevation map where the width of each bar is 1, "
            "compute how much water it can trap after raining."
        ),
        "example": "Input: height = [0,1,0,2,1,0,1,3,2,1,2,1]  =>  Output: 6",
        "idea": (
            "• Lượng nước đọng tại cột i phụ thuộc vào min(max_left, max_right) - height[i].\n"
            "• Dùng 2 con trỏ l = 0, r = n - 1 kèm 2 biến l_max, r_max.\n"
            "• Nếu l_max < r_max thì lượng nước tại l chắc chắn bị giới hạn bởi l_max -> cộng (l_max - height[l]) và tăng l; ngược lại xử lý bên r.\n"
            "• Độ phức tạp: Time O(n) | Space O(1)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    int trap(vector<int>& height) {\n"
            "        int l = 0, r = (int)height.size() - 1;\n"
            "        int l_max = height[l], r_max = height[r], water = 0;\n"
            "        while (l < r) {\n"
            "            if (l_max < r_max) {\n"
            "                l_max = max(l_max, height[++l]);\n"
            "                water += l_max - height[l];\n"
            "            } else {\n"
            "                r_max = max(r_max, height[--r]);\n"
            "                water += r_max - height[r];\n"
            "            }\n"
            "        }\n"
            "        return water;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "49",
        "title": "Group Anagrams",
        "difficulty": "Medium",
        "topics": "Array, Hash Table, String, Sorting",
        "url": "https://leetcode.com/problems/group-anagrams/",
        "description": (
            "Given an array of strings strs, group the anagrams together. You can return the answer in any order."
        ),
        "example": 'Input: strs = ["eat","tea","tan","ate","nat","bat"]  =>  Output: [["bat"],["nat","tan"],["ate","eat","tea"]]',
        "idea": (
            "• Hai chuỗi là anagram của nhau nếu sau khi sắp xếp các ký tự (sort(key.begin(), key.end())) chúng giống hệt nhau.\n"
            "• Dùng unordered_map<string, vector<string>> gom các từ có cùng chuỗi đã sort vào chung 1 nhóm.\n"
            "• Độ phức tạp: Time O(n * k log k) | Space O(n * k)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    vector<vector<string>> groupAnagrams(vector<string>& strs) {\n"
            "        unordered_map<string, vector<string>> groups;\n"
            "        for (const string& s : strs) {\n"
            "            string key = s;\n"
            "            sort(key.begin(), key.end());\n"
            "            groups[key].push_back(s);\n"
            "        }\n"
            "        vector<vector<string>> res;\n"
            "        for (auto& [k, v] : groups) res.push_back(move(v));\n"
            "        return res;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "53",
        "title": "Maximum Subarray",
        "difficulty": "Medium",
        "topics": "Array, Divide and Conquer, Dynamic Programming",
        "url": "https://leetcode.com/problems/maximum-subarray/",
        "description": (
            "Given an integer array nums, find the subarray with the largest sum, and return its sum."
        ),
        "example": "Input: nums = [-2,1,-3,4,-1,2,1,-5,4]  =>  Output: 6 (Subarray [4,-1,2,1] has largest sum 6)",
        "idea": (
            "• Thuật toán Kadane: duyệt qua mảng và duy trì tổng mảng con kết thúc tại vị trí hiện tại (cur_sum).\n"
            "• Nếu cur_sum < 0 thì bỏ đoạn trước đó đi, bắt đầu lại từ phần tử hiện tại: cur_sum = max(x, cur_sum + x).\n"
            "• Cập nhật max_sum = max(max_sum, cur_sum) ở mỗi bước.\n"
            "• Độ phức tạp: Time O(n) | Space O(1)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    int maxSubArray(vector<int>& nums) {\n"
            "        int cur_sum = nums[0], max_sum = nums[0];\n"
            "        for (size_t i = 1; i < nums.size(); ++i) {\n"
            "            cur_sum = max(nums[i], cur_sum + nums[i]);\n"
            "            max_sum = max(max_sum, cur_sum);\n"
            "        }\n"
            "        return max_sum;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "56",
        "title": "Merge Intervals",
        "difficulty": "Medium",
        "topics": "Array, Sorting",
        "url": "https://leetcode.com/problems/merge-intervals/",
        "description": (
            "Given an array of intervals where intervals[i] = [start_i, end_i], merge all overlapping intervals, "
            "and return an array of the non-overlapping intervals that cover all the intervals in the input."
        ),
        "example": "Input: intervals = [[1,3],[2,6],[8,10],[15,18]]  =>  Output: [[1,6],[8,10],[15,18]]",
        "idea": (
            "• Sắp xếp các đoạn theo điểm bắt đầu start_i tăng dần.\n"
            "• Duyệt từng đoạn: nếu in[0] <= merged.back()[1] (bị chồng lấp), gộp chúng lại bằng cách cập nhật merged.back()[1] = max(merged.back()[1], in[1]).\n"
            "• Nếu không chồng lấp, push_back đoạn mới vào kết quả.\n"
            "• Độ phức tạp: Time O(n log n) | Space O(n)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    vector<vector<int>> merge(vector<vector<int>>& intervals) {\n"
            "        sort(intervals.begin(), intervals.end());\n"
            "        vector<vector<int>> merged = {intervals[0]};\n"
            "        for (size_t i = 1; i < intervals.size(); ++i) {\n"
            "            if (intervals[i][0] <= merged.back()[1])\n"
            "                merged.back()[1] = max(merged.back()[1], intervals[i][1]);\n"
            "            else\n"
            "                merged.push_back(intervals[i]);\n"
            "        }\n"
            "        return merged;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "70",
        "title": "Climbing Stairs",
        "difficulty": "Easy",
        "topics": "Math, Dynamic Programming, Memoization",
        "url": "https://leetcode.com/problems/climbing-stairs/",
        "description": (
            "You are climbing a staircase. It takes n steps to reach the top. "
            "Each time you can either climb 1 or 2 steps. In how many distinct ways can you climb to the top?"
        ),
        "example": "Input: n = 3  =>  Output: 3 (1+1+1, 1+2, 2+1)",
        "idea": (
            "• Quy hoạch động (giống dãy Fibonacci): để lên bậc i, ta có thể bước 1 bậc từ (i-1) hoặc bước 2 bậc từ (i-2).\n"
            "• Công thức: dp[i] = dp[i-1] + dp[i-2]. Chỉ cần 2 biến a, b để tối ưu bộ nhớ O(1).\n"
            "• Độ phức tạp: Time O(n) | Space O(1)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    int climbStairs(int n) {\n"
            "        int a = 1, b = 1;\n"
            "        for (int i = 1; i < n; ++i) {\n"
            "            int next = a + b;\n"
            "            a = b;\n"
            "            b = next;\n"
            "        }\n"
            "        return b;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "121",
        "title": "Best Time to Buy and Sell Stock",
        "difficulty": "Easy",
        "topics": "Array, Dynamic Programming",
        "url": "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/",
        "description": (
            "You are given an array prices where prices[i] is the price of a given stock on the i-th day. "
            "Maximize your profit by choosing a single day to buy one stock and choosing a different day in the future to sell."
        ),
        "example": "Input: prices = [7,1,5,3,6,4]  =>  Output: 5 (Buy on day 2 at price 1, sell on day 5 at price 6)",
        "idea": (
            "• Duyệt qua giá cổ phiếu từng ngày và lưu lại mức giá thấp nhất đã gặp (min_price).\n"
            "• Lợi nhuận nếu bán ở ngày hôm nay là (price - min_price); cập nhật max_profit = max(max_profit, price - min_price).\n"
            "• Độ phức tạp: Time O(n) | Space O(1)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    int maxProfit(vector<int>& prices) {\n"
            "        int min_price = INT_MAX, max_profit = 0;\n"
            "        for (int p : prices) {\n"
            "            min_price = min(min_price, p);\n"
            "            max_profit = max(max_profit, p - min_price);\n"
            "        }\n"
            "        return max_profit;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "128",
        "title": "Longest Consecutive Sequence",
        "difficulty": "Medium",
        "topics": "Array, Hash Table, Union Find",
        "url": "https://leetcode.com/problems/longest-consecutive-sequence/",
        "description": (
            "Given an unsorted array of integers nums, return the length of the longest consecutive elements sequence. "
            "You must write an algorithm that runs in O(n) time."
        ),
        "example": "Input: nums = [100,4,200,1,3,2]  =>  Output: 4 (The longest consecutive sequence is [1, 2, 3, 4])",
        "idea": (
            "• Đưa toàn bộ số vào một Hash Set (unordered_set<int>) để tra cứu O(1).\n"
            "• Chỉ bắt đầu đếm chuỗi liên tiếp từ số x nếu (x - 1) KHÔNG có trong set (tức x là phần tử đầu tiên của chuỗi).\n"
            "• Nhờ vậy mỗi phần tử chỉ được duyệt tối đa 2 lần -> đảm bảo chuẩn O(n).\n"
            "• Độ phức tạp: Time O(n) | Space O(n)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    int longestConsecutive(vector<int>& nums) {\n"
            "        unordered_set<int> num_set(nums.begin(), nums.end());\n"
            "        int longest = 0;\n"
            "        for (int x : num_set) {\n"
            "            if (!num_set.count(x - 1)) {\n"
            "                int len = 1;\n"
            "                while (num_set.count(x + len)) ++len;\n"
            "                longest = max(longest, len);\n"
            "            }\n"
            "        }\n"
            "        return longest;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "198",
        "title": "House Robber",
        "difficulty": "Medium",
        "topics": "Array, Dynamic Programming",
        "url": "https://leetcode.com/problems/house-robber/",
        "description": (
            "You are a professional robber planning to rob houses along a street. Adjacent houses have security systems "
            "connected; you cannot rob two adjacent houses. Return the maximum amount of money you can rob tonight."
        ),
        "example": "Input: nums = [2,7,9,3,1]  =>  Output: 12 (Rob house 1 (2) + house 3 (9) + house 5 (1) = 12)",
        "idea": (
            "• Tại mỗi ngôi nhà có số tiền x, ta có 2 lựa chọn: không cướp nhà này (giữ nguyên prev1) hoặc cướp nhà này (nhận prev2 + x).\n"
            "• Công thức quy hoạch động: cur = max(prev1, prev2 + x).\n"
            "• Độ phức tạp: Time O(n) | Space O(1)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    int rob(vector<int>& nums) {\n"
            "        int prev2 = 0, prev1 = 0;\n"
            "        for (int x : nums) {\n"
            "            int cur = max(prev1, prev2 + x);\n"
            "            prev2 = prev1;\n"
            "            prev1 = cur;\n"
            "        }\n"
            "        return prev1;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "200",
        "title": "Number of Islands",
        "difficulty": "Medium",
        "topics": "Array, DFS, BFS, Matrix",
        "url": "https://leetcode.com/problems/number-of-islands/",
        "description": (
            "Given an m x n 2D binary grid which represents a map of '1's (land) and '0's (water), "
            "return the number of islands."
        ),
        "example": "Input: grid with 3 disconnected '1' regions  =>  Output: 3",
        "idea": (
            "• Duyệt qua từng ô (r, c) của ma trận.\n"
            "• Mỗi khi gặp ô đất '1', tăng biến đếm islands++ và gọi DFS để đánh dấu toàn bộ các ô '1' kề nhau thành '0' (đã thăm).\n"
            "• Độ phức tạp: Time O(m * n) | Space O(m * n)."
        ),
        "answer": (
            "class Solution {\n"
            "    void dfs(vector<vector<char>>& g, int r, int c) {\n"
            "        if (r < 0 || r >= (int)g.size() || c < 0 || c >= (int)g[0].size() || g[r][c] != '1') return;\n"
            "        g[r][c] = '0';\n"
            "        dfs(g, r + 1, c); dfs(g, r - 1, c);\n"
            "        dfs(g, r, c + 1); dfs(g, r, c - 1);\n"
            "    }\n"
            "public:\n"
            "    int numIslands(vector<vector<char>>& grid) {\n"
            "        int islands = 0;\n"
            "        for (int r = 0; r < (int)grid.size(); ++r)\n"
            "            for (int c = 0; c < (int)grid[0].size(); ++c)\n"
            "                if (grid[r][c] == '1') { ++islands; dfs(grid, r, c); }\n"
            "        return islands;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "238",
        "title": "Product of Array Except Self",
        "difficulty": "Medium",
        "topics": "Array, Prefix Sum",
        "url": "https://leetcode.com/problems/product-of-array-except-self/",
        "description": (
            "Given an integer array nums, return an array answer such that answer[i] is equal to the product "
            "of all the elements of nums except nums[i], in O(n) time and without using the division operation."
        ),
        "example": "Input: nums = [1,2,3,4]  =>  Output: [24,12,8,6]",
        "idea": (
            "• Tích ngoại trừ nums[i] bằng (Tích các số bên trái i) * (Tích các số bên phải i).\n"
            "• Lượt 1 (trái sang phải): lưu tích tiền tố (prefix product) vào mảng res.\n"
            "• Lượt 2 (phải sang trái): nhân dồn tích hậu tố (suffix product) vào res[i].\n"
            "• Độ phức tạp: Time O(n) | Space O(1) (ngoài mảng kết quả)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    vector<int> productExceptSelf(vector<int>& nums) {\n"
            "        int n = nums.size();\n"
            "        vector<int> res(n, 1);\n"
            "        for (int i = 0, prefix = 1; i < n; ++i) {\n"
            "            res[i] = prefix;\n"
            "            prefix *= nums[i];\n"
            "        }\n"
            "        for (int i = n - 1, suffix = 1; i >= 0; --i) {\n"
            "            res[i] *= suffix;\n"
            "            suffix *= nums[i];\n"
            "        }\n"
            "        return res;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "322",
        "title": "Coin Change",
        "difficulty": "Medium",
        "topics": "Array, Dynamic Programming, BFS",
        "url": "https://leetcode.com/problems/coin-change/",
        "description": (
            "You are given an integer array coins representing coins of different denominations and an integer amount. "
            "Return the fewest number of coins that you need to make up that amount (or -1 if impossible)."
        ),
        "example": "Input: coins = [1,2,5], amount = 11  =>  Output: 3 (11 = 5 + 5 + 1)",
        "idea": (
            "• Quy hoạch động Bottom-Up: gọi dp[a] là số đồng xu ít nhất để tạo ra số tiền a.\n"
            "• Khởi tạo vector<int> dp(amount + 1, amount + 1), với dp[0] = 0.\n"
            "• Với mỗi mức tiền a từ 1..amount và mỗi mệnh giá c trong coins: nếu a >= c thì dp[a] = min(dp[a], dp[a - c] + 1).\n"
            "• Độ phức tạp: Time O(amount * coins.size()) | Space O(amount)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    int coinChange(vector<int>& coins, int amount) {\n"
            "        vector<int> dp(amount + 1, amount + 1);\n"
            "        dp[0] = 0;\n"
            "        for (int a = 1; a <= amount; ++a)\n"
            "            for (int c : coins)\n"
            "                if (a >= c) dp[a] = min(dp[a], dp[a - c] + 1);\n"
            "        return dp[amount] <= amount ? dp[amount] : -1;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "347",
        "title": "Top K Frequent Elements",
        "difficulty": "Medium",
        "topics": "Array, Hash Table, Heap, Bucket Sort",
        "url": "https://leetcode.com/problems/top-k-frequent-elements/",
        "description": (
            "Given an integer array nums and an integer k, return the k most frequent elements."
        ),
        "example": "Input: nums = [1,1,1,2,2,3], k = 2  =>  Output: [1,2]",
        "idea": (
            "• Đếm tần suất xuất hiện của từng phần tử bằng unordered_map<int, int>.\n"
            "• Dùng Bucket Sort (vector<vector<int>> buckets(n + 1), trong đó buckets[freq] chứa các số xuất hiện đúng freq lần) và duyệt từ tần suất cao xuống thấp.\n"
            "• Độ phức tạp: Time O(n) | Space O(n)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    vector<int> topKFrequent(vector<int>& nums, int k) {\n"
            "        unordered_map<int, int> cnt;\n"
            "        for (int x : nums) ++cnt[x];\n"
            "        vector<vector<int>> buckets(nums.size() + 1);\n"
            "        for (auto& [num, freq] : cnt) buckets[freq].push_back(num);\n"
            "        vector<int> res;\n"
            "        for (int f = (int)buckets.size() - 1; f >= 0 && (int)res.size() < k; --f)\n"
            "            for (int num : buckets[f])\n"
            "                if ((int)res.size() < k) res.push_back(num);\n"
            "        return res;\n"
            "    }\n"
            "};"
        ),
    },
    {
        "id": "739",
        "title": "Daily Temperatures",
        "difficulty": "Medium",
        "topics": "Array, Stack, Monotonic Stack",
        "url": "https://leetcode.com/problems/daily-temperatures/",
        "description": (
            "Given an array of integers temperatures represents the daily temperatures, return an array answer "
            "such that answer[i] is the number of days you have to wait after the i-th day to get a warmer temperature."
        ),
        "example": "Input: temperatures = [73,74,75,71,69,72,76,73]  =>  Output: [1,1,4,2,1,1,0,0]",
        "idea": (
            "• Dùng Monotonic Decreasing Stack (stack<int>) lưu chỉ số ngày chưa tìm được ngày ấm hơn.\n"
            "• Khi gặp nhiệt độ temperatures[i] cao hơn nhiệt độ tại đỉnh stack, lấy prev = st.top(), st.pop() và gán res[prev] = i - prev.\n"
            "• Độ phức tạp: Time O(n) | Space O(n)."
        ),
        "answer": (
            "class Solution {\n"
            "public:\n"
            "    vector<int> dailyTemperatures(vector<int>& temperatures) {\n"
            "        int n = temperatures.size();\n"
            "        vector<int> res(n, 0);\n"
            "        stack<int> st;\n"
            "        for (int i = 0; i < n; ++i) {\n"
            "            while (!st.empty() && temperatures[st.top()] < temperatures[i]) {\n"
            "                int prev = st.top(); st.pop();\n"
            "                res[prev] = i - prev;\n"
            "            }\n"
            "            st.push(i);\n"
            "        }\n"
            "        return res;\n"
            "    }\n"
            "};"
        ),
    },
]

# Extra problems on doocs/leetcode (GitHub Raw) to expand the random pool
DOOCS_PATHS = [
    ("0000-0099", "0005.Longest Palindromic Substring"),
    ("0000-0099", "0019.Remove Nth Node From End of List"),
    ("0000-0099", "0021.Merge Two Sorted Lists"),
    ("0000-0099", "0023.Merge k Sorted Lists"),
    ("0000-0099", "0033.Search in Rotated Sorted Array"),
    ("0000-0099", "0039.Combination Sum"),
    ("0000-0099", "0048.Rotate Image"),
    ("0000-0099", "0055.Jump Game"),
    ("0000-0099", "0062.Unique Paths"),
    ("0000-0099", "0076.Minimum Window Substring"),
    ("0000-0099", "0079.Word Search"),
    ("0000-0099", "0098.Validate Binary Search Tree"),
    ("0100-0199", "0102.Binary Tree Level Order Traversal"),
    ("0100-0199", "0104.Maximum Depth of Binary Tree"),
    ("0100-0199", "0125.Valid Palindrome"),
    ("0100-0199", "0139.Word Break"),
    ("0100-0199", "0141.Linked List Cycle"),
    ("0100-0199", "0152.Maximum Product Subarray"),
    ("0100-0199", "0153.Find Minimum in Rotated Sorted Array"),
    ("0100-0199", "0167.Two Sum II - Input Array Is Sorted"),
    ("0200-0299", "0206.Reverse Linked List"),
    ("0200-0299", "0207.Course Schedule"),
    ("0200-0299", "0215.Kth Largest Element in an Array"),
    ("0200-0299", "0217.Contains Duplicate"),
    ("0200-0299", "0226.Invert Binary Tree"),
    ("0200-0299", "0230.Kth Smallest Element in a BST"),
    ("0200-0299", "0235.Lowest Common Ancestor of a Binary Search Tree"),
    ("0200-0299", "0242.Valid Anagram"),
    ("0300-0399", "0300.Longest Increasing Subsequence"),
    ("0700-0799", "0704.Binary Search"),
]


def is_leetcode_command(msg_text: str) -> bool:
    """Return True if msg_text contains a !leetcode command (and is not our own bot output)."""
    lower = msg_text.lower().strip()
    if "🧩 leetcode #" in lower or "💡 idea / approach" in lower or "✅ answer (c++" in lower:
        return False
    return any(cmd in lower for cmd in ["!leetcode", "/leetcode", "!lc"])


def _load_seen_ids() -> set[str]:
    if SEEN_LEETCODE_FILE.exists():
        return set(
            ln.strip()
            for ln in SEEN_LEETCODE_FILE.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        )
    return set()


def _record_seen_id(prob_id: str, seen: set[str]) -> None:
    seen.add(prob_id)
    with SEEN_LEETCODE_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{prob_id}\n")


def _clean_html(raw_html: str) -> str:
    txt = re.sub(r"<pre>\s*", "\n", raw_html)
    txt = re.sub(r"</pre>", "\n", txt)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = html.unescape(txt)
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    return "\n".join(lines)


def _fetch_doocs_problem(range_dir: str, folder: str) -> dict | None:
    """Fetch and parse a LeetCode problem + Idea + C++ Answer from doocs/leetcode on GitHub Raw."""
    quoted_folder = urllib.parse.quote(folder)
    url = f"https://raw.githubusercontent.com/doocs/leetcode/main/solution/{range_dir}/{quoted_folder}/README_EN.md"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        md = resp.read().decode("utf-8", errors="ignore")

    m_title = re.search(r"#\s*\[(\d+)\.\s*([^\]]+)\]\((https://leetcode\.com/problems/[^\)]+)\)", md)
    if not m_title:
        return None
    prob_id, title, lc_url = m_title.group(1), m_title.group(2).strip(), m_title.group(3).strip()

    m_diff = re.search(r"difficulty:\s*(\w+)", md)
    difficulty = m_diff.group(1) if m_diff else "Medium"

    m_desc = re.search(r"<!-- description:start -->(.*?)<!-- description:end -->", md, flags=re.S)
    desc_raw = _clean_html(m_desc.group(1)) if m_desc else ""
    parts = re.split(r"Example 1:", desc_raw, maxsplit=1)
    description = parts[0].strip()[:450]
    example = ("Example 1: " + parts[1].split("Example 2:")[0].split("Constraints:")[0].strip()[:220]) if len(parts) > 1 else ""

    m_sol = re.search(r"### Solution 1:([^\n]*)\n(.*?)#### C\+\+\s*```cpp\n(.*?)```", md, flags=re.S)
    if not m_sol:
        return None
    sol_title = m_sol.group(1).strip()
    sol_idea = _clean_html(m_sol.group(2)).strip()[:500]
    sol_code = m_sol.group(3).strip()

    return {
        "id": str(int(prob_id)),
        "title": title,
        "difficulty": difficulty,
        "topics": sol_title or "Algorithms & Data Structures",
        "url": lc_url,
        "description": description,
        "example": example.replace("\n", " | "),
        "idea": f"• Approach ({sol_title or 'Optimal'}):\n{sol_idea}",
        "answer": sol_code,
    }


def pick_random_problem(difficulty_filter: str = "") -> dict:
    """Pick an unseen random LeetCode problem (preferring curated Vietnamese+English explanations + GitHub Raw pool)."""
    seen = _load_seen_ids()
    candidates = [
        p for p in CURATED_PROBLEMS
        if p["id"] not in seen
        and (not difficulty_filter or p["difficulty"].lower() == difficulty_filter.lower())
    ]

    # Also try fetching from doocs/leetcode on GitHub Raw 35% of the time or if curated pool is exhausted
    if not candidates or (not difficulty_filter and random.random() < 0.35):
        unseen_doocs = [
            item for item in DOOCS_PATHS
            if str(int(item[1].split(".")[0])) not in seen
        ]
        if unseen_doocs:
            random.shuffle(unseen_doocs)
            for range_dir, folder in unseen_doocs[:2]:
                try:
                    fetched = _fetch_doocs_problem(range_dir, folder)
                    if fetched and (not difficulty_filter or fetched["difficulty"].lower() == difficulty_filter.lower()):
                        _record_seen_id(fetched["id"], seen)
                        LAST_LEETCODE_FILE.write_text(json.dumps(fetched, ensure_ascii=False, indent=2), encoding="utf-8")
                        return fetched
                except Exception:
                    continue

    # If all curated problems have been seen, reset the seen list for curated problems
    if not candidates:
        candidates = [
            p for p in CURATED_PROBLEMS
            if not difficulty_filter or p["difficulty"].lower() == difficulty_filter.lower()
        ] or list(CURATED_PROBLEMS)

    chosen = random.choice(candidates)
    _record_seen_id(chosen["id"], seen)
    LAST_LEETCODE_FILE.write_text(json.dumps(chosen, ensure_ascii=False, indent=2), encoding="utf-8")
    return chosen


def get_current_or_random_problem() -> dict:
    if LAST_LEETCODE_FILE.exists():
        try:
            return json.loads(LAST_LEETCODE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return pick_random_problem()


def format_leetcode_response(prob: dict, show_problem: bool, show_idea: bool, show_answer: bool) -> str:
    diff_badge = {"easy": "🟢 Easy", "medium": "🟡 Medium", "hard": "🔴 Hard"}.get(
        prob["difficulty"].lower(), prob["difficulty"]
    )
    lines = [
        f"🧩 LEETCODE #{prob['id']}: {prob['title']} ({diff_badge})",
        f"🔗 Link: {prob['url']} | 🏷️ Topics: {prob.get('topics', '')}",
        "",
    ]

    if show_problem:
        lines.append(f"📝 Problem: {prob['description']}")
        if prob.get("example"):
            lines.append(f"📌 Example: {prob['example']}")
        lines.append("")

    if show_idea:
        lines.append("💡 IDEA / APPROACH (Hướng giải tối ưu):")
        for ln in prob["idea"].splitlines():
            lines.append(f"   {ln}")
        lines.append("")

    if show_answer:
        lines.append("✅ ANSWER (C++ Solution):")
        for ln in prob["answer"].splitlines():
            lines.append(f"   │ {ln}")
        lines.append("")

    if not show_idea or not show_answer:
        tips = []
        if not show_idea:
            tips.append("'!leetcode ideal' (xem hướng giải)")
        if not show_answer:
            tips.append("'!leetcode answer' (xem code C++)")
        tips.append("'!leetcode full' (bài mới + cả ideal & answer)")
        lines.append("💬 Options: Gõ " + " | ".join(tips))

    return "\n".join(lines).strip()


def handle_leetcode_command(msg_text: str) -> str:
    """Parse !leetcode command and return formatted response string."""
    lower = msg_text.lower()

    # Check difficulty filter
    diff_filter = ""
    for d in ("easy", "medium", "hard"):
        if re.search(rf"\b{d}\b", lower):
            diff_filter = d
            break

    want_idea = any(re.search(rf"\b{w}\b", lower) for w in ("idea", "ideal", "hint", "approach", "full", "all"))
    want_answer = any(re.search(rf"\b{w}\b", lower) for w in ("answer", "ans", "solution", "sol", "code", "full", "all"))
    explicit_random = any(re.search(rf"\b{w}\b", lower) for w in ("random", "new", "full", "all")) or bool(diff_filter)

    if explicit_random or (not want_idea and not want_answer):
        prob = pick_random_problem(diff_filter)
        return format_leetcode_response(
            prob,
            show_problem=True,
            show_idea=want_idea,
            show_answer=want_answer,
        )

    # Follow-up command (!leetcode ideal or !leetcode answer) for the currently active problem
    prob = get_current_or_random_problem()
    return format_leetcode_response(
        prob,
        show_problem=False,
        show_idea=want_idea or want_answer,
        show_answer=want_answer,
    )
