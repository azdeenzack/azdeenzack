use git_koi::history::{AccountSnapshot, RepositoryObservation, RepositoryVisibility, calculate_language_shares, calculate_language_shares_with_private};

#[test]
fn private_is_explicit_and_internal_and_forks_stay_excluded() {
    let mut snapshot = AccountSnapshot { account_id: 1, repositories: vec![], contribution_history: None, language_colors: None };
    for (id, visibility, is_fork, language) in [
        (1, RepositoryVisibility::Public, false, "Rust"),
        (2, RepositoryVisibility::Private, false, "Python"),
        (3, RepositoryVisibility::Internal, false, "Go"),
        (4, RepositoryVisibility::Private, true, "Java"),
    ] {
        snapshot.repositories.push(RepositoryObservation { repository_id: id, visibility, is_fork, primary_language: Some(language.into()) });
    }
    let default = calculate_language_shares(&snapshot).unwrap();
    assert_eq!(default.len(), 1);
    assert_eq!(default["Rust"], 1.0);
    let opted_in = calculate_language_shares_with_private(&snapshot, true).unwrap();
    assert_eq!(opted_in.len(), 2);
    assert_eq!(opted_in["Rust"], 0.5);
    assert_eq!(opted_in["Python"], 0.5);
}
